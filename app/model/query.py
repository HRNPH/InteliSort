from typing import List, Any, Union, NewType, Literal, Optional
from pydantic import BaseModel

from app.model.base_response import BaseResponseModel

class QuerySimilarityModel(BaseModel):
    vector_score: float
    state: Optional[str] = None
    comment: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    sub_district: Optional[str] = None

class QuerySimilarityResponseModel(BaseResponseModel):
    content: List[
        QuerySimilarityModel
    ]
    
