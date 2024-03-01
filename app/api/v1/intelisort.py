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

redis = None

# define logger format
logger.remove(0)
logger.add(sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}", serialize=False)

async def startup_event():
    logger.info("Connecting to database...")
    global redis
    redis = await aioredis.from_url(os.environ.get("REDISCLOUD_URL", "redis://localhost"))  # Default to localhost if env var is missing
    logger.info("Loading csv into Redis")
    logger.info(os.getcwd())
    await load_csv_to_redis(redis=redis)

# Define your shutdown event handler
async def shutdown_event():
    logger.info("Disconnecting from database...")
    await redis.close()

router = APIRouter()
# Attach the event handlers to the FastAPI app
router.add_event_handler("startup", startup_event)
router.add_event_handler("shutdown", shutdown_event)

# -- Routes --
@router.get('/', tags=["Health Check"])
async def health_check(request: Request) -> base_response.BaseStatusResponseModel:
    return base_response.BaseStatusResponseModel(success=True, content="Intelisort API is up and running!")

# upload CSV data
@router.post('/import/csv', tags=["import data (Under Development)"])
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
    
    return kumyarb.KumYarbResponseModel(success=True, content=result)

# -- Function --
async def load_csv_to_redis(redis):
    df = pd.read_csv("app/api/v1/static/kumyarb.csv")
    # using HIGH MID LOW
    for level in ['HIGH', 'MID', 'LOW']:
        key = f"words:{level.lower()}"  # Redis key pattern, e.g., "words:high"
        values = df[level].dropna().tolist()
        if values:
            await redis.sadd(key, *values)


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