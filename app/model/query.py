from typing import List, Any, Union, NewType, Literal, Optional
from pydantic import BaseModel

from app.model.base_response import BaseResponseModel


class QuerySimilarityInput(BaseModel):
    ticket_id: Optional[str] = None
    type: Optional[str] = None
    organization: Optional[str] = None
    comment: Optional[str] = None
    coords: Optional[str] = None
    photo: Optional[str] = None
    photo_after: Optional[str] = None
    address: Optional[str] = None
    subdistrict: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    timestamp: Optional[str] = None
    state: Optional[str] = None
    star: Optional[float] = None
    count_reopen: Optional[int] = None
    last_activity: Optional[str] = None


class QuerySimilarityRequest(BaseModel):
    queries: List[QuerySimilarityInput]
    top_k: int = 5


class QueryDistanceInput(BaseModel):
    coords: Optional[str] = None
    ticket_id: Optional[str] = None
    

class QueryDistanceRequest(BaseModel):
    queries: List[QueryDistanceInput]
    top_k: int = 5
    radius: int = 600


class QuerySimilarityModel(BaseModel):
    vector_score: float
    state: Optional[str] = None
    comment: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    sub_district: Optional[str] = None


class QuerySimilarityResponseModel(BaseResponseModel):
    success: bool
    content: List[Union[List[QuerySimilarityModel], Any]]


class QueryDistanceModel(BaseModel):
    distance: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data: Optional[dict] = None


class QueryDistanceResponseModel(BaseResponseModel):
    success: bool
    content: List[Union[List[QueryDistanceModel], Any]]
