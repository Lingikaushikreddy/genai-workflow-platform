from fastapi import APIRouter, HTTPException
from app.models.schemas import WorkflowRequest, WorkflowResponse
from app.services.workflow_engine import run_workflow

router = APIRouter()

@router.post("/workflow/run", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    try:
        result = run_workflow(request.query)
        return WorkflowResponse(
            status="success",
            result=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
