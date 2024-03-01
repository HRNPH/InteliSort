from typing import List, Any, Union, NewType, Literal
from pydantic import BaseModel

from app.model.base_response import BaseResponseModel
class Meta(BaseModel):
    word_num: int
    word: str
    severity: Literal["HIGH", "MID", "LOW"]

class KumYarbModel(BaseModel):
    original: str
    censored: str
    meta: List[Meta]

class KumYarbResponseModel(BaseResponseModel):
    content: List[
        KumYarbModel
    ]
    