import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
REQUEST_COUNT = Counter(
    "catalog_matcher_http_requests_total",
    "Completed HTTP requests.",
    ("method", "route", "status"),
)
REQUEST_DURATION = Histogram(
    "catalog_matcher_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
)
REQUESTS_IN_PROGRESS = Gauge(
    "catalog_matcher_http_requests_in_progress",
    "HTTP requests currently being processed.",
)


def register_observability(application: FastAPI) -> None:
    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @application.middleware("http")
    async def observe_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        logger = structlog.get_logger("http")
        started = time.perf_counter()
        REQUESTS_IN_PROGRESS.inc()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            elapsed = time.perf_counter() - started
            REQUEST_COUNT.labels(request.method, route_path, str(status_code)).inc()
            REQUEST_DURATION.labels(request.method, route_path).observe(elapsed)
            REQUESTS_IN_PROGRESS.dec()
            logger.info(
                "request_completed",
                method=request.method,
                route=route_path,
                status=status_code,
                duration_ms=round(elapsed * 1000, 3),
            )
            structlog.contextvars.clear_contextvars()


def _request_id(header_value: str | None) -> str:
    if header_value and REQUEST_ID_PATTERN.fullmatch(header_value):
        return header_value
    return str(uuid4())
