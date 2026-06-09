from pydantic import BaseModel

class SearchRequest(BaseModel):
    query:str
    
class SearchResponse(BaseModel):
    answer: str
    sources: list