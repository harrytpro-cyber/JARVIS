from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.v1.routers.auth import get_current_user
from services.web_search_service import search

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    max_results: int = 3


@router.post("/web")
async def web_search(body: SearchRequest, _=Depends(get_current_user)):
    results = await search(body.query)
    return {"query": body.query, "results": results[:body.max_results]}
