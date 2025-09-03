from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import WorkflowRequest, WorkflowResponse, WorkflowMetadata
from app.api.deps import get_workflow_engine, verify_api_key, check_rate_limit, get_providers
from app.services.workflow import WorkflowEngine
from app.providers import Providers
import time

router = APIRouter(
    prefix="/workflow",
    tags=["workflow"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)]
)

@router.post("/run", response_model=WorkflowResponse)
async def run_workflow(
    request: WorkflowRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
    providers: Providers = Depends(get_providers)
):
    start = time.perf_counter()
    result = engine.run(request.query)
    
    latency = (time.perf_counter() - start) * 1000
    
    return WorkflowResponse(
        result=result.get("messages", [{}])[0].content if result.get("messages") else "",
        context_used=result.get("sources", []),
        metadata=WorkflowMetadata(
            model=providers.llm._llm_type,
            latency_ms=latency,
            request_id="test-req",
            retrieved_count=len(result.get("sources", [])),
            mock_mode=providers.mock_mode
        )
    )

@router.post("/stream")
async def stream_workflow(
    request: WorkflowRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    async def sse_generator():
        async for event in engine.stream(request.query):
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")
