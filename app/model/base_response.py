from pydantic import BaseModel
from typing import List, Any

class BaseResponseModel(BaseModel):
    success: bool
    content: Any = None
    error: str = None
    
class BaseStatusResponseModel(BaseResponseModel):
    status: str

class BaseContentExampleResponseModel(BaseResponseModel):
    content: List[str]