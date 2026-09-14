from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import repository
from database.db import get_db
from schemas import SearchResult
from services.ai_service import parse_search_query
from services.security import current_session
router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(current_session)])
@router.get("", response_model=SearchResult)
def smart_search(q: str = "", db: Session = Depends(get_db)):
    filters = parse_search_query(q); documents = repository.list_documents(db, q=filters.get("q"), document_type=filters.get("document_type"), due_within_days=filters.get("expiry_within_days"), expiry_year=filters.get("expiry_year"), sort_by=filters.get("sort_by", "expiry_date"), order=filters.get("order", "asc"))
    answer = f"Found {len(documents)} documents." + (f" Type: {filters['document_type']}." if filters.get("document_type") else "")
    return {"query": q, "filters": filters, "count": len(documents), "answer": answer, "documents": documents}
