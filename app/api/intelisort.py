import sys
from fastapi import APIRouter, Request, status, File, UploadFile
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger
from app.db.prisma import prisma
from app.function import example
from app.function.validator.data_import import validate_csv
from app.model import base_response
from dotenv import load_dotenv
load_dotenv()

# define logger format
logger.remove(0)
logger.add(sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}", serialize=False)

# onstart
async def lifespan(router: APIRouter):
    # db connection
    logger.info("Connecting to database...")
    await prisma.connect()
    yield  # this is where the execution will pause and wait for shutdown
    # stop db connection on shutdown
    logger.info("Disconnecting from database...")
    await prisma.disconnect()

router = APIRouter(lifespan=lifespan) # handle startup and shutdown events

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