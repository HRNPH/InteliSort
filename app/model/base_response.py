from pydantic import BaseModel
from typing import List, Any

class BaseResponseModel(BaseModel):
    success: bool
    data: Any = None
    error: str = None
    
class BaseHelloExampleResponseModel(BaseResponseModel):
    data: str
    
class BaseContentExampleResponseModel(BaseResponseModel):
    data: List[str]