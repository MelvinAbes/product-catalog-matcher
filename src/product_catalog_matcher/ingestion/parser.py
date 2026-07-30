import csv
import io
import json
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from pydantic import ValidationError

from product_catalog_matcher.domain import IssueSeverity
from product_catalog_matcher.ingestion.schemas import SupplierProductInput

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "source_record_id": (
        "source_record_id",
        "id",
        "product_id",
        "item_id",
        "supplier_product_id",
    ),
    "name": ("name", "title", "product_name", "item_name"),
    "brand": ("brand", "manufacturer", "maker"),
    "category": ("category", "category_path", "product_group", "group"),
    "gtin": ("gtin", "ean", "ean13", "upc", "barcode"),
    "sku": ("sku", "supplier_sku", "item_number"),
    "manufacturer_part_number": (
        "manufacturer_part_number",
        "mpn",
        "model_number",
        "part_number",
    ),
    "description": ("description", "details"),
    "pack_quantity": ("pack_quantity", "pack", "pack_size", "items_per_pack"),
    "unit_value": ("unit_value", "size_value", "amount", "net_content"),
    "unit_code": ("unit_code", "size_unit", "unit", "uom"),
}

SUPPORTED_SUFFIXES = {".csv", ".json"}


class FeedStructureError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class RowIssue:
    row_number: int | None
    field: str | None
    code: str
    severity: IssueSeverity
    message: str


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    raw_data: dict[str, Any]
    product: SupplierProductInput | None
    issues: tuple[RowIssue, ...]


@dataclass(frozen=True)
class FeedParseResult:
    rows: tuple[ParsedRow, ...]
    format: str


def parse_feed(
    *,
    file_name: str,
    content: bytes,
    max_bytes: int,
    max_rows: int,
) -> FeedParseResult:
    if len(content) > max_bytes:
        raise FeedStructureError(
            "file_too_large",
            f"Feed is {len(content)} bytes; the configured limit is {max_bytes} bytes.",
        )
    if b"\x00" in content:
        raise FeedStructureError("invalid_text", "Feed contains null bytes.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise FeedStructureError("invalid_encoding", "Feed must be UTF-8 encoded.") from error

    suffix = PurePath(file_name).suffix.casefold()
    if suffix not in SUPPORTED_SUFFIXES:
        raise FeedStructureError("unsupported_format", "Only CSV and JSON feeds are supported.")

    raw_rows = _parse_csv(text) if suffix == ".csv" else _parse_json(text)
    if len(raw_rows) > max_rows:
        raise FeedStructureError(
            "too_many_rows",
            f"Feed has {len(raw_rows)} rows; the configured limit is {max_rows}.",
        )

    rows = tuple(
        _validate_row(row_number=index, raw_data=raw)
        for index, raw in enumerate(raw_rows, start=2 if suffix == ".csv" else 1)
    )
    return FeedParseResult(rows=rows, format=suffix.removeprefix("."))


def _parse_csv(text: str) -> list[dict[str, Any]]:
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    if not reader.fieldnames:
        raise FeedStructureError("missing_header", "CSV feed has no header row.")

    normalized_headers = [_normalize_header(header) for header in reader.fieldnames]
    if len(normalized_headers) != len(set(normalized_headers)):
        raise FeedStructureError("duplicate_header", "CSV feed contains duplicate headers.")
    if not any(header in FIELD_ALIASES["name"] for header in normalized_headers):
        raise FeedStructureError("missing_name_column", "CSV feed has no recognized name column.")

    rows: list[dict[str, Any]] = []
    for raw in reader:
        if None in raw:
            raise FeedStructureError(
                "column_count_mismatch",
                "A CSV row contains more values than the header.",
            )
        if all(value is None or not value.strip() for value in raw.values()):
            continue
        rows.append({_normalize_header(key): value for key, value in raw.items()})
    return rows


def _parse_json(text: str) -> list[dict[str, Any]]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise FeedStructureError(
            "invalid_json",
            f"JSON parsing failed at line {error.lineno}, column {error.colno}.",
        ) from error

    if isinstance(document, dict):
        document = document.get("products")
    if not isinstance(document, list):
        raise FeedStructureError(
            "invalid_json_shape",
            "JSON feed must be an array or an object containing a products array.",
        )
    if not all(isinstance(row, dict) for row in document):
        raise FeedStructureError("invalid_json_row", "Every JSON product must be an object.")
    return [{_normalize_header(str(key)): value for key, value in row.items()} for row in document]


def _normalize_header(header: str) -> str:
    return "_".join(header.strip().casefold().replace("-", " ").split())


def _canonicalize_fields(raw_data: dict[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for target, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in raw_data:
                canonical[target] = raw_data[alias]
                break
    return canonical


def _validate_row(*, row_number: int, raw_data: dict[str, Any]) -> ParsedRow:
    canonical = _canonicalize_fields(raw_data)
    issues: list[RowIssue] = []
    try:
        product = SupplierProductInput.model_validate(canonical)
    except ValidationError as error:
        product = None
        for detail in error.errors(include_url=False, include_context=False, include_input=False):
            field = str(detail["loc"][0]) if detail["loc"] else None
            issues.append(
                RowIssue(
                    row_number=row_number,
                    field=field,
                    code=f"invalid_{field}" if field else "invalid_row",
                    severity=IssueSeverity.ERROR,
                    message=str(detail["msg"]),
                )
            )
    return ParsedRow(
        row_number=row_number,
        raw_data=raw_data,
        product=product,
        issues=tuple(issues),
    )
