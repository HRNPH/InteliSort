from app.config.config import (
    TEXT_KEY_NAME,
    EMBEDDING_KEY_NAME,
    TEXT_INDEX_NAME,
    PREFIX_INDEX_KEY,
    VECTOR_DIMENSION,
    LOCATION_KEY_NAME,
)
import numpy as np
from redis import Redis
from redis.commands.search.field import (
    NumericField,
    TagField,
    TextField,
    VectorField,
)
from pydantic import BaseModel
from app.model import base_response, kumyarb, query

from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import asyncio
import modal
from typing import Literal
import base64
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()


# Helper functions
def call_sentence_encoder(sentences: list[str]) -> list[list[float]]:
    """
    Calls the sentence-encoder function in the modal package.
    params: sentences: list[str] - a list of sentences to encode
    returns: list[list[float]] - a list of lists of floats, representing the embeddings of the sentences
    """
    try:
        inf_fx = modal.Function.lookup(
            "sentence-encoder",
            "sentence_encoder",
            environment_name="main",
        )
        result: list[list[float]] = inf_fx.remote(sentences)
        return result

    except Exception as e:  # will be raised from modal if inf_fx.remote fails
        raise e


def replace_nan_with_empty_string(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_nan_with_empty_string(value)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_nan_with_empty_string(obj[i])
    elif isinstance(obj, float) and np.isnan(obj):
        return ""
    return obj


def preprocess_coords_dict(data: dict) -> dict:
    coords = data["coords"]
    longitude = float(coords.split(",")[0])
    latitude = float(coords.split(",")[1])
    location_memeber_key = f"{LOCATION_KEY_NAME}:{data['ticket_id']}"
    member_data = {
        "longitude": longitude,
        "latitude": latitude,
        "name": location_memeber_key,
    }
    return member_data


def preprocess_prompt_dict(data: dict) -> str:
    data["comment"] = data["comment"].replace("ปัญหา:", "")
    return data["comment"]


def preprocess_raw_data(data: dict) -> dict:
    if isinstance(data, BaseModel):
        data = data.dict()
    data = {k: v if v is not None else "" for k, v in data.items()}
    data = replace_nan_with_empty_string(data)

    return data


async def add_geospatial_index(data, pipeline):
    preprocess_coords = preprocess_coords_dict(data)

    longitude = preprocess_coords["longitude"]
    latitude = preprocess_coords["latitude"]
    member_name = preprocess_coords["name"]

    await pipeline.geoadd(LOCATION_KEY_NAME, [longitude, latitude, member_name])


async def preprocess_and_store_data(data, r):
    data = preprocess_raw_data(data)
    preprocess_prompt = preprocess_prompt_dict(data)

    data_key = f"{TEXT_KEY_NAME}:{data['ticket_id']}"
    pipeline = r.pipeline(transaction=False)
    preprocess_prompt = {"raw_data": data, "preprocess_prompt": preprocess_prompt}
    await pipeline.json().set(data_key, "$", preprocess_prompt)

    await add_geospatial_index(data, pipeline)

    await pipeline.execute()


async def store_embeddings(key, embeddings, r):
    pipeline = r.pipeline(transaction=False)
    for embedding in embeddings:
        await pipeline.json().set(key, "$", embedding)
    await pipeline.execute()


async def add_data(data: dict, r):
    await preprocess_and_store_data(data, r)


async def batch_add_data(data: list[dict], r):
    for d in data:
        await preprocess_and_store_data(d, r)


# Database helper
async def clear_database(r):
    """Clear the Redis database."""
    await r.flushall()


async def drop_index(r):
    drop_index_command = ["FT.DROPINDEX", TEXT_INDEX_NAME]  # , -DD]
    await r.execute_command(*drop_index_command)


# TODO : batch inference
async def generate_embeddings_redis(r):
    keys = await r.keys(f"{TEXT_KEY_NAME}:*")
    keys = sorted(keys)
    texts = await r.json().mget(keys, "$.preprocess_prompt")
    texts = [t for sublist in texts for t in sublist]
    embeddings = call_sentence_encoder(texts)
    embeddings = embeddings

    pipeline = r.pipeline(transaction=False)
    for key, embedding in zip(keys, embeddings):
        await pipeline.json().set(key, "$.embedding", embedding)

    await pipeline.execute()


# index helper
async def create_index_text(r):
    try:
        schema = (
            # TextField('$.preprocess_prompt', no_stem=True, as_name='preprocess_prompt'),
            TextField("$.raw_data.state", no_stem=True, as_name="state"),
            TextField("$.raw_data.comment", no_stem=True, as_name="comment"),
            TextField("$.raw_data.type", no_stem=True, as_name="type"),
            TextField("$.raw_data.address", no_stem=True, as_name="address"),
            TextField("$.raw_data.district", no_stem=True, as_name="district"),
            TextField("$.raw_data.province", no_stem=True, as_name="province"),
            TextField("$.raw_data.subdistrict", no_stem=True, as_name="subdistrict"),
            VectorField(
                f"$.{EMBEDDING_KEY_NAME}",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": VECTOR_DIMENSION,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="vector",
            ),
        )
        definition = IndexDefinition(
            prefix=[PREFIX_INDEX_KEY], index_type=IndexType.JSON
        )
        await r.ft(TEXT_INDEX_NAME).create_index(fields=schema, definition=definition)

    except:
        await r.ft(TEXT_INDEX_NAME).info()
        return f"Index {TEXT_INDEX_NAME} already exists"

    return f"Index {TEXT_INDEX_NAME} created"


async def get_info_index(r):
    info = await r.ft(TEXT_INDEX_NAME).info()

    num_docs = info["num_docs"]
    indexing_failures = info["hash_indexing_failures"]
    total_indexing_time = info["total_indexing_time"]
    percent_indexed = float(info["percent_indexed"]) * 100

    return f"{num_docs} docs ({percent_indexed}%) indexed w/ {indexing_failures} failures in {float(total_indexing_time):.2f} msecs"


# query helper


async def query_embeddings_by_similarity(
    r, embeddings: List[List[float]], top_k: int = 5
) -> List[List[Dict]]:
    similarity_query = create_similarity_query(top_k)
    return await asyncio.gather(
        *[
            process_single_embedding_similarity_query(r, embedding, similarity_query)
            for embedding in embeddings
        ]
    )


def create_similarity_query(top_k: int) -> Query:
    return (
        Query(f"(*)=>[KNN {top_k} @vector $query_vector AS similarity_score]")
        .sort_by("similarity_score")
        .return_fields(
            "state",
            "comment",
            "type",
            "address",
            "district",
            "province",
            "subdistrict",
            "similarity_score",
        )
        .dialect(2)
    )


async def process_single_embedding_similarity_query(
    r, embedding: List[float], q: Query
) -> List[Dict]:
    results = await r.ft(TEXT_INDEX_NAME).search(
        q, {"query_vector": np.array(embedding, dtype=np.float32).tobytes()}
    )
    return [process_result_similarity_query(result) for result in results.docs]


def process_result_similarity_query(result) -> Dict:
    similarity_score = round(1 - float(result.similarity_score), 3)
    return {
        "similarity_score": similarity_score,
        "state": result.state,
        "comment": result.comment,
        "type": result.type,
        "address": result.address,
        "district": result.district,
        "province": result.province,
        "subdistrict": result.subdistrict,
    }


async def query_all_texts_from_similarity(r: Redis, queries: List[dict], top_k=5):
    queries = [preprocess_raw_data(q) for q in queries]
    queries = [preprocess_prompt_dict(q) for q in queries]
    # embeddings = np.random.rand(len(queries), VECTOR_DIMENSION).tolist()
    embeddings = call_sentence_encoder(queries)
    return await query_embeddings_by_similarity(r, embeddings, top_k=top_k)


async def query_all_texts_from_distance(
    r: Redis, queries: List[dict], top_k: int = 5, radius: int = 600
) -> List[List[Dict]]:
    top_k += 1
    queries = [preprocess_raw_data(q) for q in queries]
    await ensure_geospatial_indices(r, queries)
    return await process_queries_distance_query(r, queries, top_k, radius)


async def ensure_geospatial_indices(r: Redis, queries: List[dict]) -> None:
    tasks = [
        add_geospatial_index(r, query)
        for query in queries
        if not r.exists(f"{LOCATION_KEY_NAME}:{query['ticket_id']}")
    ]
    await asyncio.gather(*tasks)


async def process_queries_distance_query(
    r: Redis, queries: List[dict], top_k: int, radius: int
) -> List[List[Dict]]:
    return await asyncio.gather(
        *[process_single_distance_query(r, q, top_k, radius) for q in queries]
    )


async def process_single_distance_query(
    r: Redis, q: dict, top_k: int, radius: int
) -> List[Dict]:
    name = preprocess_coords_dict(q)["name"]
    results = await r.georadiusbymember(
        LOCATION_KEY_NAME,
        name,
        radius,
        unit="m",
        withdist=True,
        withcoord=True,
        count=top_k,
    )
    return await process_results_distance_output(r, results, q["ticket_id"])


async def process_results_distance_output(
    r: Redis, results: List, query_ticket_id: str
) -> List[Dict]:
    processed_results = []
    for result in results:
        member_name, distance, (latitude, longitude) = result
        ticket_id = member_name.decode("utf-8").split(":")[-1]

        if ticket_id == query_ticket_id:
            continue

        data = await fetch_result_data_distance_query(r, ticket_id)
        processed_results.append(
            {
                "distance": distance,
                "latitude": latitude,
                "longitude": longitude,
                "data": data.get("raw_data", {}) if data else {},
            }
        )
    return processed_results


async def fetch_result_data_distance_query(r: Redis, ticket_id: str) -> Dict:
    data_key = f"{TEXT_KEY_NAME}:{ticket_id}"
    try:
        return (await r.json().get(data_key, "$"))[0]
    except Exception:
        return None
