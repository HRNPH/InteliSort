from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from app.api.v1 import intelisort
from fastapi import FastAPI, HTTPException, Request, Security, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from dotenv import load_dotenv
import os

load_dotenv()

is_production = os.getenv("ENVIRONMENT") != "development"
title = "Intelisort API"
description = "City Issues Priority Sorting, Grouping and Curse Detection API"
summary = "API Specs for Intelisort Service"
API_KEY = os.getenv("API_KEY")

app = FastAPI(
    title=title,
    description=description,
    summary=summary,
    docs_url=None,
    redoc_url=None,
) if is_production else FastAPI(
    title=title,
    description=description,
    summary=summary,
)

# Define the allowed hosts from settings.ALLOW_HOSTS and settings.ALLOW_CORS

# Middleware to allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key header dependency
api_key_header = APIKeyHeader(name="api-key")

def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

# Include the router with the dependency for API key validation
app.include_router(
    intelisort.router,
    prefix="/intelisort",
    tags=["intelisort"],
    dependencies=[Depends(validate_api_key)],
    responses={404: {"description": "Not found"}},
)

@app.get("/")
def root(request: Request):
    # Access and log the host header
    host_header = request.headers.get("host")
    print("host_header:", host_header)
    # request ip
    ip = request.client.host
    print("ip:", ip)
    return {"message": "Up And Running!"}

@app.get('/docs', include_in_schema=False)
def get_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
