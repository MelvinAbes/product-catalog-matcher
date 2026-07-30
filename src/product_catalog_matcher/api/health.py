from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]


def create_health_router(readiness_check: Callable[[], bool]) -> APIRouter:
    router = APIRouter(tags=["operations"])

    @router.get("/health/live")
    def liveness() -> HealthResponse:
        return HealthResponse(status="ok")

    @router.get(
        "/health/ready",
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
    )
    def readiness(response: Response) -> HealthResponse:
        if not readiness_check():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(status="not_ready")
        return HealthResponse(status="ok")

    return router
