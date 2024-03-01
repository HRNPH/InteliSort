from fastapi.responses import JSONResponse
from app.api.v1 import intelisort
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
load_dotenv()

is_production = os.getenv("ENVIRONMENT") != "development"
app = FastAPI(
    title="Intelisort API",
    description="City Issues Priority Sorting, Grouping and Curse Detection API",
    summary="API Specs for Intelisort Service",
    docs_url=None,
    redoc_url=None    
) if is_production else FastAPI()

# Define the allowed hosts from settings.ALLOW_HOSTS and settings.ALLOW_CORS

# Add Custom Middleware Validators
@app.middleware('http')
async def validate_ip(request: Request, call_next):
    # Get client IP
    # ip = str(request.client.host)
    # # get api key in header
    # api_key = request.headers.get("api-key")
    # # Check if IP is allowed
    # if api_key != os.environ.get("API_KEY") and is_production:
    #     data = {
    #         'message': f'IP {ip} is not allowed to access this resource.'
    #     }
    #     return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=data)

    # # Proceed if IP is allowed
    return await call_next(request)

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intelisort.router, prefix="/intelisort")

@app.get("/")
def root(request: Request):
    # Access and log the host header
    host_header = request.headers.get("host")
    print("host_header:", host_header)
    # request ip
    ip = request.client.host
    print("ip:", ip)
    return {"message": "Up And Running!"}