from collections.abc import Callable

from fastapi import FastAPI

from product_catalog_matcher.api.health import create_health_router
from product_catalog_matcher.config import Settings, get_settings
from product_catalog_matcher.database import database_is_ready
from product_catalog_matcher.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    readiness_check: Callable[[], bool] | None = None,
) -> FastAPI:
    application_settings = settings or get_settings()
    configure_logging(application_settings)

    application = FastAPI(
        title=application_settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.include_router(create_health_router(readiness_check or database_is_ready))
    return application


app = create_app()
