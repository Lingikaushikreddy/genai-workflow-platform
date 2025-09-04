from fastapi import APIRouter, Depends
from app.models.schemas import IngestRequest, IngestResponse
from app.api.deps import get_ingestion_service, verify_api_key, check_rate_limit
from app.services.ingestion import IngestionService

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)]
)

@router.post("", response_model=IngestResponse)
async def ingest_documents(
    request: IngestRequest,
    service: IngestionService = Depends(get_ingestion_service)
):
    result = service.ingest(request.documents)
    return IngestResponse(
        documents_received=result["documents_received"],
        chunks_ingested=result["chunks_ingested"],
        chunk_ids=result["chunk_ids"]
    )
