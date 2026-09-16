from fastapi import APIRouter, Depends

from app.api.deps import get_providers

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness():
    return {"status": "up"}


@router.get("/ready")
def readiness(providers=Depends(get_providers)):
    return {"status": "ready", "mock_mode": providers.mock_mode}
