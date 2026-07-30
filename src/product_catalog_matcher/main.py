from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from product_catalog_matcher.api.catalog import router as catalog_router
from product_catalog_matcher.api.errors import register_exception_handlers
from product_catalog_matcher.api.health import create_health_router
from product_catalog_matcher.api.imports import router as imports_router
from product_catalog_matcher.api.matching import router as matching_router
from product_catalog_matcher.api.reports import router as reports_router
from product_catalog_matcher.api.reviews import router as reviews_router
from product_catalog_matcher.api.suppliers import router as suppliers_router
from product_catalog_matcher.api.ui import router as ui_router
from product_catalog_matcher.config import Settings, get_settings
from product_catalog_matcher.database import database_is_ready
from product_catalog_matcher.logging import configure_logging
from product_catalog_matcher.observability import register_observability


def create_app(
    settings: Settings | None = None,
    readiness_check: Callable[[], bool] | None = None,
) -> FastAPI:
    application_settings = settings or get_settings()
    configure_logging(application_settings)

    application = FastAPI(
        title=application_settings.app_name,
        version="0.1.0",
        description=(
            "Import supplier feeds, inspect data quality, produce explainable catalog "
            "matches, and resolve ambiguous proposals."
        ),
        license_info={
            "name": "Apache License 2.0",
            "identifier": "Apache-2.0",
        },
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parent / "static"),
        name="static",
    )
    application.include_router(create_health_router(readiness_check or database_is_ready))
    application.include_router(ui_router)
    application.include_router(suppliers_router)
    application.include_router(imports_router)
    application.include_router(matching_router)
    application.include_router(reviews_router)
    application.include_router(reports_router)
    application.include_router(catalog_router)
    register_exception_handlers(application)
    register_observability(application)
    return application


app = create_app()
