from fastapi import HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import Settings
from app.core.ratelimit import RateLimiter, RateLimitExceeded
from app.providers import Providers
from app.services.ingestion import IngestionService
from app.services.workflow import WorkflowEngine

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_providers(request: Request) -> Providers:
    return request.app.state.providers


def get_workflow_engine(request: Request) -> WorkflowEngine:
    return request.app.state.workflow_engine


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    settings = get_settings(request)
    if settings.API_KEY is not None:
        if not api_key or api_key != settings.API_KEY.get_secret_value():
            raise HTTPException(status_code=403, detail="Invalid API Key")


def check_rate_limit(request: Request):
    limiter: RateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    try:
        limiter.check(client_ip)
    except RateLimitExceeded:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
