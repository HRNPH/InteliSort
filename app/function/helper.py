from config import TEXT_KEY_NAME, EMBEDDING_KEY_NAME, TEXT_INDEX_NAME, PREFIX_INDEX_KEY, VECTOR_DIMENSION
import numpy as np
from redis.commands.search.field import (
    NumericField,
    TagField,
    TextField,
    VectorField,
)

from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

# Helper functions

def call_sentence_encoder(sentences: list[str]) -> list[list[float]]:
    return np.random.rand(len(sentences), 384)

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

def preprocess_prompt_dict(data : dict) -> str:
    data['type'] = data['type'].strip('{}')
    data['type'] = "ไม่มีชนิด" if data['type'] == "" else data['type']
    
    data['comment'] = data['comment'].replace('ปัญหา:', '')
    return data['type'] + ' ' + data['comment']

def preprocess_raw_data(data : dict) -> dict:
    data = {k : v if v is not None else "" for k, v in data.items()}
    data = replace_nan_with_empty_string(data)
    
    return data

def preprocess_and_store_data(data, r):
    data = preprocess_raw_data(data)
    preprocess_prompt = preprocess_prompt_dict(data)

    data_key = f"{TEXT_KEY_NAME}:{data['ticket_id']}"
    pipeline = r.pipeline(transaction = False)
    preprocess_prompt = {
        "raw_data" : data,
        "preprocess_prompt" : preprocess_prompt
    }
    pipeline.json().set(data_key, '$', preprocess_prompt)
    
    pipeline.execute()

def store_embeddings(key, embeddings, r):
    pipeline = r.pipeline(transaction = False)
    for embedding in embeddings:
        pipeline.json().set(key, '$', embedding)
    pipeline.execute()

def add_data(data : dict):
    preprocess_and_store_data(data)

def batch_add_data(data : list[dict]):
    for d in data:
        preprocess_and_store_data(d)

# Database helper
def clear_database(r):
    """Clear the Redis database."""
    r.flushall()

def drop_index(r):
    drop_index_command = ["FT.DROPINDEX", TEXT_INDEX_NAME] #, -DD] 
    r.execute_command(*drop_index_command)

#TODO : batch inference
def generate_embeddings_redis(r):
    keys = sorted(r.keys(f'{TEXT_KEY_NAME}:*'))
    texts = r.json().mget(keys, "$.preprocess_prompt")
    texts = [t for sublist in texts for t in sublist]
    embeddings = call_sentence_encoder(texts)
    embeddings = embeddings.astype(np.float32).tolist()

    pipeline = r.pipeline(transaction=False)
    for key, embedding in zip(keys, embeddings):
        pipeline.json().set(key, "$.embedding", embedding)

    pipeline.execute()

# index helper
def create_index_text(r):
    try:
        schema = (
            # TextField('$.preprocess_prompt', no_stem=True, as_name='preprocess_prompt'),
            TextField("$.raw_data.state",no_stem=True, as_name="state"),
            TextField("$.raw_data.comment",no_stem=True, as_name="comment"),
            TextField("$.raw_data.type",no_stem=True, as_name="type"),
            TextField("$.raw_data.address",no_stem=True, as_name="address"),
            TextField("$.raw_data.district",no_stem=True, as_name="district"),
            TextField("$.raw_data.province",no_stem=True, as_name="province"),
            TextField("$.raw_data.subdistrict",no_stem=True, as_name="subdistrict"),
            VectorField(f'$.{EMBEDDING_KEY_NAME}', 'FLAT', {
                'TYPE': 'FLOAT32',
                'DIM': VECTOR_DIMENSION,
                'DISTANCE_METRIC': 'COSINE'
            }, as_name='vector')
        )
    except:
        r.ft(TEXT_INDEX_NAME).info()
        print(f"Index {TEXT_INDEX_NAME} already exists")
        
    definition = IndexDefinition(prefix=[PREFIX_INDEX_KEY], index_type=IndexType.JSON)

    r.ft(TEXT_INDEX_NAME).create_index(fields=schema, definition=definition)

def get_info_index(r):
    info = r.ft(TEXT_INDEX_NAME).info()

    num_docs = info['num_docs']
    indexing_failures = info['hash_indexing_failures']
    total_indexing_time = info['total_indexing_time']
    percent_indexed = float(info['percent_indexed']) * 100

    print(f"{num_docs} docs ({percent_indexed}%) indexed w/ {indexing_failures} failures in {float(total_indexing_time):.2f} msecs")

# query helper

def query_all_embeddings(r, embeddings, top_k=5):
    results_list = []
    query = (
        Query(f"(*)=>[KNN {top_k} @vector $query_vector AS vector_score]")
        .sort_by("vector_score")
        .return_fields(
            "state",
            "comment",
            "type",
            "address",
            "district",
            "province",
            "subdistrict",
            "vector_score",
        )
        .dialect(2)
    )
    for embedding in embeddings:
        results = (
            r.ft(TEXT_INDEX_NAME)
            .search(
                query, {"query_vector": np.array(embedding, dtype=np.float32).tobytes()}
            )
            .docs
        )
        for result in results:
            vector_score = round(1 - float(result.vector_score), 3)
            results_list.append(
                {
                    "vector_score": vector_score,
                    "state": result.state,
                    "comment": result.comment,
                    "type": result.type,
                    "address": result.address,
                    "district": result.district,
                    "province": result.province,
                    "subdistrict": result.subdistrict,
                }
            )
        break
    return results_list


def query_all_texts(queries, top_k=5):
    queries = [preprocess_prompt_dict(text) for text in queries]
    embeddings = call_sentence_encoder(queries)
    return query_all_embeddings(embeddings, top_k=top_k)