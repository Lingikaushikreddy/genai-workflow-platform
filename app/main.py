import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import documents, health, workflow
from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.logging import request_id_var, setup_logging
from app.core.ratelimit import RateLimiter
from app.providers import build_providers
from app.services.ingestion import IngestionService
from app.services.workflow import WorkflowEngine

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    404: "not_found",
    405: "method_not_allowed",
    401: "unauthorized",
    403: "forbidden",
}


def _error_body(code: str, message: str, details: list | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_var.get(),
            "details": details,
        }
    }


class _BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """Reject over-sized request bodies before they are buffered into memory.

    FastAPI/Starlette read the whole body before Pydantic validation runs and
    uvicorn imposes no default cap, so without this an unauthenticated client
    could OOM the process with a single large POST. Checks Content-Length up
    front and also counts streamed bytes to cover chunked uploads.
    """

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.max_bytes
        ):
            await self._reject(send)
            return

        total = 0
        response_started = False

        async def counting_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            if response_started:
                raise
            await self._reject(send)

    async def _reject(self, send) -> None:
        body = json.dumps(
            _error_body("request_too_large", "Request body exceeds the allowed size.")
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    """Pure-ASGI middleware: request-id propagation + structured access logs.

    Implemented at the ASGI layer (rather than BaseHTTPMiddleware) so streaming
    responses pass through unbuffered.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = Headers(scope=scope).get("x-request-id") or uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = {"code": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status["code"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_logging(settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        providers = build_providers(settings)
        app.state.settings = settings
        app.state.providers = providers
        app.state.rate_limiter = RateLimiter(settings.RATE_LIMIT_PER_MINUTE)
        app.state.workflow_engine = WorkflowEngine(
            llm=providers.llm,
            vector_store=providers.vector_store,
            retrieval_k=settings.RETRIEVAL_K,
        )
        app.state.ingestion_service = IngestionService(
            vector_store=providers.vector_store,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        logger.info(
            "application started",
            extra={
                "mock_mode": providers.mock_mode,
                "environment": settings.ENVIRONMENT,
                "auth_required": settings.API_KEY is not None,
                "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
            },
        )
        yield

    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Starlette's add_middleware inserts at position 0, so the LAST added is the
    # OUTERMOST. Adding BodySize -> CORS -> RequestContext yields the desired
    # request flow RequestContext -> CORS -> BodySize -> routes: the request id
    # is set and CORS headers are applied before the body guard can emit a 413.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BYTES)
    if settings.BACKEND_CORS_ORIGINS:
        # Explicit origins only: wildcard + credentials is invalid per the CORS
        # spec, and Settings rejects "*" at load time.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "validation_error",
                "Request validation failed.",
                details=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(code, message)
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "An internal error occurred."),
        )

    app.include_router(health.router)
    app.include_router(workflow.router, prefix=settings.API_V1_STR)
    app.include_router(documents.router, prefix=settings.API_V1_STR)

    @app.get("/", include_in_schema=False)
    def root():
        return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/docs"}

    return app


app = create_app()
