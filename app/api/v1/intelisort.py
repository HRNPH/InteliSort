import sys
from fastapi import (
    APIRouter,
    Request,
    status,
    File,
    UploadFile,
    BackgroundTasks,
    HTTPException,
)
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger
from app.function import example
from app.function.validator.data_import import validate_csv
from app.model import base_response, kumyarb, query
import os
from redis import asyncio as aioredis
import pandas as pd
import numpy as np
from pythainlp.tokenize import word_tokenize
import pythainlp
from app.function.helper import *
import io
import csv
import codecs
from typing import List

redis = None

# define logger format
logger.remove(0)
logger.add(
    sys.stderr,
    format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}",
    serialize=False,
)


async def startup_event():
    logger.info("Connecting to database...")
    global redis
    redis = await aioredis.from_url(
        os.environ.get("REDISCLOUD_URL", "redis://localhost")
    )  # Default to localhost if env var is missing
    logger.info("Loading csv into Redis")
    logger.info(os.getcwd())
    await load_csv_to_redis(redis=redis)
    logger.info("Kumyarb words loaded into Redis")


# Define your shutdown event handler
async def shutdown_event():
    logger.info("Disconnecting from database...")
    await redis.close()


router = APIRouter()
# Attach the event handlers to the FastAPI app
router.add_event_handler("startup", startup_event)
router.add_event_handler("shutdown", shutdown_event)


# -- Routes --
@router.get("/", tags=["Health Check"])
async def health_check(request: Request) -> base_response.BaseResponseModel:
    return base_response.BaseResponseModel(
        success=True, content="Intelisort API is up and running!"
    )


# upload CSV data
from starlette.status import HTTP_409_CONFLICT

processing_lock = False
chunk_counter = 0


@router.post("/import/csv", tags=["1. import data"])
async def import_csv(
    background_tasks: BackgroundTasks,
    csv_file: UploadFile = File(...),
) -> base_response.BaseStatusResponseModel:
    global processing_lock, chunk_counter
    if processing_lock:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Another file is already being processed. Please try again later.",
        )

    processing_lock = True
    chunk_counter = 0

    logger.info(f"Uploading file: {csv_file.filename}")
    valid_columns = [
        "ticket_id",
        "type",
        "organization",
        "comment",
        "coords",
        "photo",
        "photo_after",
        "address",
        "subdistrict",
        "district",
        "province",
        "timestamp",
        "state",
        "star",
        "count_reopen",
        "last_activity",
    ]
    try:
        if not csv_file.filename.endswith(".csv"):
            raise TypeError(
                f"Invalid file type, only accept .csv file, but got {csv_file.filename}"
            )
        csv_content = csv.reader(codecs.iterdecode(csv_file.file, "utf-8-sig"))
        header = next(csv_content)
        if not all([column in valid_columns for column in header]):
            raise ValueError(
                f"Invalid file column, Required: [{', '.join(valid_columns)}] but got [{', '.join(header)}]"
            )
        data_json = []
        chunk_size = 200
        for row in csv_content:
            data_json.append(dict(zip(header, row)))
            if len(data_json) == chunk_size:
                chunk_counter += 1
                background_tasks.add_task(
                    process_chunk, data_json, redis, chunk_counter
                )
                data_json = []
        if data_json:
            chunk_counter += 1
            background_tasks.add_task(process_chunk, data_json, redis, chunk_counter)
        logger.info(f"File {csv_file.filename} is read successfully")
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        processing_lock = False
        return base_response.BaseStatusResponseModel(
            success=False, status=f"Error reading file: {str(e)}"
        )

    background_tasks.add_task(complete_processing, redis)
    return base_response.BaseStatusResponseModel(
        success=True, status="CSV file processing started in the background"
    )


async def process_chunk(data_chunk, redis, chunk_number):
    logger.info(f"Processing data chunk: {chunk_number}")
    await batch_add_data(data_chunk, redis)
    await generate_embeddings_redis(redis)


async def complete_processing(redis):
    global processing_lock
    response = await create_index_text(redis)
    logger.info(f"Indexing completed successfully, {response}")
    info = await get_info_index(redis)
    logger.info(f"Data processing completed successfully, {info}")
    # await drop_index(redis) # auto delete index wtf
    processing_lock = False
    return response


@router.get("/index_info", tags=["Functionality"])
async def get_index_info():
    info = await get_info_index(redis)
    return {"success": True, "content": info}


@router.get("/complete_processing", tags=["preprocessing data"])
async def complete_processing_api():
    response = await complete_processing(redis)
    return {"success": True, "content": response}


@router.post("/query_from_similarity", tags=["2. query data"])
async def query_data_from_similarity(queries: List[dict]) -> query.QuerySimilarityResponseModel:
    result = await query_all_texts_from_similarity(redis, queries=queries, top_k=5)
    return query.QuerySimilarityResponseModel(success=True, content=result)


@router.post("/query_from_distance", tags=["2. query data"])
async def query_data_from_distance(queries: List[dict]) -> query.QueryDistanceResponseModel:
    result = await query_all_texts_from_distance(redis, queries, top_k=5, radius=600)
    return query.QueryDistanceResponseModel(success=True, content=result)


@router.post("/curse_check", tags=["Functionality"])
async def curse_check(text: List[str]):
    result = []
    for t in text:
        meta, new_text = await check_kumyarb(t)
        result.append({"original": t, "censored": new_text, "meta": meta})

    return kumyarb.KumYarbResponseModel(success=True, content=result)


# -- Function --
async def load_csv_to_redis(redis):
    df = pd.read_csv("app/api/v1/static/kumyarb.csv")
    # using HIGH MID LOW
    for level in ["HIGH", "MID", "LOW"]:
        key = f"words:{level.lower()}"  # Redis key pattern, e.g., "words:high"
        values = df[level].dropna().tolist()
        if values:
            await redis.sadd(key, *values)


async def check_kumyarb(text):
    arr = []
    new_text = ""
    for i, v in enumerate(word_tokenize(text, engine="newmm")):
        # Check membership in the Redis sets
        if await redis.sismember("words:high", v):
            arr.append({"word_num": i, "word": v, "severity": "HIGH"})
            new_text += "xxx"
        elif await redis.sismember("words:mid", v):
            arr.append({"word_num": i, "word": v, "severity": "MID"})
            new_text += "xxx"
        elif await redis.sismember("words:low", v):
            arr.append({"word_num": i, "word": v, "severity": "LOW"})
            new_text += "xxx"
        else:
            new_text += v
    return arr, new_text
