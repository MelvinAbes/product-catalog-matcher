from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from product_catalog_matcher.ingestion.parser import FeedStructureError
from product_catalog_matcher.ingestion.service import (
    DuplicateFeedError,
    ImportNotFoundError,
    SupplierCodeConflictError,
    SupplierNotFoundError,
)


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str


def problem_response(
    *,
    status_code: int,
    problem_type: str,
    title: str,
    detail: str,
) -> JSONResponse:
    problem = ProblemDetail(
        type=f"urn:product-catalog-matcher:error:{problem_type}",
        title=title,
        status=status_code,
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(FeedStructureError)
    def feed_structure_error(_request: Request, error: FeedStructureError) -> JSONResponse:
        return problem_response(
            status_code=422,
            problem_type=error.code,
            title="Invalid supplier feed",
            detail=str(error),
        )

    @application.exception_handler(SupplierNotFoundError)
    def supplier_not_found(_request: Request, error: SupplierNotFoundError) -> JSONResponse:
        return problem_response(
            status_code=404,
            problem_type="supplier_not_found",
            title="Supplier not found",
            detail=str(error),
        )

    @application.exception_handler(ImportNotFoundError)
    def import_not_found(_request: Request, error: ImportNotFoundError) -> JSONResponse:
        return problem_response(
            status_code=404,
            problem_type="import_not_found",
            title="Import batch not found",
            detail=str(error),
        )

    @application.exception_handler(DuplicateFeedError)
    def duplicate_feed(_request: Request, error: DuplicateFeedError) -> JSONResponse:
        return problem_response(
            status_code=409,
            problem_type="duplicate_feed",
            title="Duplicate supplier feed",
            detail=str(error),
        )

    @application.exception_handler(SupplierCodeConflictError)
    def supplier_code_conflict(
        _request: Request,
        error: SupplierCodeConflictError,
    ) -> JSONResponse:
        return problem_response(
            status_code=409,
            problem_type="supplier_code_conflict",
            title="Supplier code already exists",
            detail=str(error),
        )
