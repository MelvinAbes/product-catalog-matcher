from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from product_catalog_matcher.catalog.review import (
    ReviewConflictError,
    ReviewProposalNotFoundError,
    ReviewTargetNotFoundError,
)
from product_catalog_matcher.ingestion.parser import FeedStructureError
from product_catalog_matcher.ingestion.service import (
    DuplicateFeedError,
    ImportNotFoundError,
    SupplierCodeConflictError,
    SupplierNotFoundError,
)
from product_catalog_matcher.matching.service import (
    BatchAlreadyMatchedError,
    MatchBatchNotFoundError,
    ReferenceBatchMatchError,
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

    @application.exception_handler(MatchBatchNotFoundError)
    def match_batch_not_found(
        _request: Request,
        error: MatchBatchNotFoundError,
    ) -> JSONResponse:
        return problem_response(
            status_code=404,
            problem_type="match_batch_not_found",
            title="Match batch not found",
            detail=str(error),
        )

    @application.exception_handler(ReferenceBatchMatchError)
    def reference_batch_match(
        _request: Request,
        error: ReferenceBatchMatchError,
    ) -> JSONResponse:
        return problem_response(
            status_code=422,
            problem_type="reference_batch",
            title="Reference batch cannot be matched",
            detail=str(error),
        )

    @application.exception_handler(BatchAlreadyMatchedError)
    def batch_already_matched(
        _request: Request,
        error: BatchAlreadyMatchedError,
    ) -> JSONResponse:
        return problem_response(
            status_code=409,
            problem_type="batch_already_matched",
            title="Batch already matched",
            detail=str(error),
        )

    @application.exception_handler(ReviewProposalNotFoundError)
    def review_not_found(
        _request: Request,
        error: ReviewProposalNotFoundError,
    ) -> JSONResponse:
        return problem_response(
            status_code=404,
            problem_type="review_not_found",
            title="Review proposal not found",
            detail=str(error),
        )

    @application.exception_handler(ReviewTargetNotFoundError)
    def review_target_not_found(
        _request: Request,
        error: ReviewTargetNotFoundError,
    ) -> JSONResponse:
        return problem_response(
            status_code=404,
            problem_type="review_target_not_found",
            title="Review target not found",
            detail=str(error),
        )

    @application.exception_handler(ReviewConflictError)
    def review_conflict(
        _request: Request,
        error: ReviewConflictError,
    ) -> JSONResponse:
        return problem_response(
            status_code=409,
            problem_type="review_conflict",
            title="Review decision conflict",
            detail=str(error),
        )
