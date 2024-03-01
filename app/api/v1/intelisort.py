import sys
from fastapi import APIRouter, Request, status, File, UploadFile
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger
from app.function import example
from app.function.validator.data_import import validate_csv
from app.model import base_response, kumyarb
import os
from redis import asyncio as aioredis
import pandas as pd
import numpy as np
from pythainlp.tokenize import word_tokenize
import pythainlp
load_dotenv()

# define logger format
logger.remove(0)
logger.add(sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}", serialize=False)

# onstart
async def lifespan(router: APIRouter):
    # db connection
    logger.info("Connecting to database...")
    global redis
    redis = await aioredis.from_url(os.environ.get("REDISCLOUD_URL", None))
    logger.info("Loading csv into redis")
    await load_csv_to_redis(redis=redis)
    yield  # this is where the execution will pause and wait for shutdown
    # stop db connection on shutdown
    logger.info("Disconnecting from database...")

router = APIRouter(lifespan=lifespan) # handle startup and shutdown events

async def load_csv_to_redis(redis):
    df = pd.read_csv('./static/kumyarb.csv')
    # using HIGH MID LOW
    for level in ['HIGH', 'MID', 'LOW']:
        key = f"words:{level.lower()}"  # Redis key pattern, e.g., "words:high"
        values = df[level].dropna().tolist()
        if values:
            await redis.sadd(key, *values)

# -- Routes --
@router.get('/', tags=["Health Check"])
async def health_check(request: Request) -> base_response.BaseStatusResponseModel:
    return base_response.BaseStatusResponseModel(success=True, content="Hello, World!") 

@router.get('/listexample', tags=["Example"])
async def list_example(request: Request) -> base_response.BaseContentExampleResponseModel:
    return base_response.BaseContentExampleResponseModel(success=True, content=["Hello", "World!"])

@router.post('/sayhello', tags=["Example"])
async def greeting(request: Request, to: str) -> base_response.BaseStatusResponseModel:
    content = example.say_hello(to)
    return base_response.BaseStatusResponseModel(success=True, content=content)

# upload CSV data
@router.post('/import/csv', tags=["import data"])
async def import_csv(
    csv_file: UploadFile = File(...),
) -> base_response.BaseStatusResponseModel:
    logger.info(f"Uploading file: {csv_file.filename}")
    # validate file type
    is_csv, status_msg = validate_csv(file=csv_file)
    if not is_csv:
        logger.error(f"File {csv_file.filename} is not valid, {status_msg}")
        return base_response.BaseStatusResponseModel(success=is_csv, status=status_msg)
    logger.info(f"File {csv_file.filename} is valid")
    # do something with the content
    return base_response.BaseStatusResponseModel(success=is_csv, status=status_msg)

@router.post('/curse_check', tags=["Functionality"])
async def curse_check(text: list[str]):
    result = []
    for t in text:
        meta, new_text = await check_kumyarb(t)
        result.append(
            {
                "original": t,
                "censored": new_text,
                "meta": meta
            }
        )
    
    return kumyarb(content=result)

# -- Function --
async def check_kumyarb(text):
    arr = []
    new_text = ""
    for i, v in enumerate(word_tokenize(text, engine="newmm")):
        # Check membership in the Redis sets
        if await redis.sismember('words:high', v):
            arr.append({
                "word_num": i,
                "word": v,
                "severity": 'HIGH'
            })
            new_text += "xxx"
        elif await redis.sismember('words:mid', v):
            arr.append({
                "word_num": i,
                "word": v,
                "severity": 'MID'
            })
            new_text += "xxx"
        elif await redis.sismember('words:low', v):
            arr.append({
                "word_num": i,
                "word": v,
                "severity": 'LOW'
            })
            new_text += "xxx"
        else:
            new_text += v
    return arr, new_text