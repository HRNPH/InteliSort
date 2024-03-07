from typing import List, Any, Union, NewType, Literal
from pydantic import BaseModel

from app.model.base_response import BaseResponseModel

class QueryModel(BaseModel):
    vector_score: int
    state: str
    comment: str
    type: str
    address: str
    province: str
    sub_district: str

class QueryResponseModel(BaseResponseModel):
    content: List[
        QueryModel
    ]