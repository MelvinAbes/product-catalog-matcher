from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from product_catalog_matcher.catalog.review import get_review_item, list_open_reviews
from product_catalog_matcher.database import get_session
from product_catalog_matcher.reporting.summary import build_catalog_summary

router = APIRouter(tags=["interface"])
SessionDependency = Annotated[Session, Depends(get_session)]
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request, session: SessionDependency) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"summary": build_catalog_summary(session)},
    )


@router.get("/review", response_class=HTMLResponse, include_in_schema=False)
def review_queue(request: Request, session: SessionDependency) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reviews.html",
        context={"reviews": list_open_reviews(session, limit=100, offset=0)},
    )


@router.get("/review/{proposal_id}", response_class=HTMLResponse, include_in_schema=False)
def review_detail(
    proposal_id: UUID,
    request: Request,
    session: SessionDependency,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="review_detail.html",
        context={"review": get_review_item(session, proposal_id)},
    )
