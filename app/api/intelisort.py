import sys
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger
from app.db.prisma import prisma
from app.function import example
from app.model import base_response
from dotenv import load_dotenv
load_dotenv()

# define logger format
logger.remove(0)
logger.add(sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}", serialize=True)

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
async def health_check(request: Request) -> base_response.BaseHelloExampleResponseModel:
    return base_response.BaseHelloExampleResponseModel(success=True, data="Hello, World!") 

@router.get('/listexample', tags=["Example"])
async def list_example(request: Request) -> base_response.BaseContentExampleResponseModel:
    return base_response.BaseContentExampleResponseModel(success=True, data=["Hello", "World!"])

@router.post('/sayhello', tags=["Example"])
async def greeting(request: Request, to: str) -> base_response.BaseHelloExampleResponseModel:
    content = example.say_hello(to)
    return base_response.BaseHelloExampleResponseModel(success=True, data=content)