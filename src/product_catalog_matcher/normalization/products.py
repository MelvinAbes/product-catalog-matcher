import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal

from product_catalog_matcher.domain import IssueSeverity
from product_catalog_matcher.ingestion.parser import RowIssue
from product_catalog_matcher.ingestion.schemas import SupplierProductInput

NON_WORDS = re.compile(r"[^\w]+", flags=re.UNICODE)
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
UNIT_ALIASES = {
    "g": ("g", Decimal("1")),
    "gram": ("g", Decimal("1")),
    "grams": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "kilogram": ("g", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "milliliter": ("ml", Decimal("1")),
    "millilitre": ("ml", Decimal("1")),
    "l": ("ml", Decimal("1000")),
    "liter": ("ml", Decimal("1000")),
    "litre": ("ml", Decimal("1000")),
    "pc": ("count", Decimal("1")),
    "pcs": ("count", Decimal("1")),
    "piece": ("count", Decimal("1")),
    "pieces": ("count", Decimal("1")),
    "count": ("count", Decimal("1")),
}


@dataclass(frozen=True)
class NormalizedProduct:
    source_record_id: str
    name: str
    normalized_name: str
    brand: str | None
    normalized_brand: str | None
    category: str | None
    normalized_category: str | None
    gtin: str | None
    normalized_gtin: str | None
    sku: str | None
    manufacturer_part_number: str | None
    normalized_mpn: str | None
    description: str | None
    normalized_description: str | None
    pack_quantity: Decimal | None
    unit_value: Decimal | None
    unit_code: str | None
    fingerprint: str


@dataclass(frozen=True)
class NormalizationResult:
    product: NormalizedProduct
    issues: tuple[RowIssue, ...]


def normalize_product(product: SupplierProductInput, *, row_number: int) -> NormalizationResult:
    issues: list[RowIssue] = []
    normalized_gtin = normalize_gtin(product.gtin)
    if product.gtin and normalized_gtin is None:
        issues.append(
            RowIssue(
                row_number=row_number,
                field="gtin",
                code="invalid_gtin",
                severity=IssueSeverity.WARNING,
                message="Identifier does not have a valid GTIN length and check digit.",
            )
        )

    unit_value, unit_code = normalize_unit(product.unit_value, product.unit_code)
    if product.unit_code and unit_code is None:
        issues.append(
            RowIssue(
                row_number=row_number,
                field="unit_code",
                code="unknown_unit",
                severity=IssueSeverity.WARNING,
                message=f"Unit {product.unit_code!r} is not in the normalization table.",
            )
        )
        unit_value = product.unit_value
        unit_code = normalize_text(product.unit_code)

    normalized_name = normalize_text(product.name)
    normalized_brand = normalize_optional_text(product.brand)
    normalized_category = normalize_category(product.category)
    normalized_mpn = normalize_identifier(product.manufacturer_part_number)
    normalized_description = normalize_optional_text(product.description)
    fingerprint = build_fingerprint(
        {
            "normalized_name": normalized_name,
            "normalized_brand": normalized_brand,
            "normalized_category": normalized_category,
            "normalized_gtin": normalized_gtin,
            "normalized_mpn": normalized_mpn,
            "pack_quantity": product.pack_quantity,
            "unit_value": unit_value,
            "unit_code": unit_code,
        }
    )
    return NormalizationResult(
        product=NormalizedProduct(
            source_record_id=product.source_record_id,
            name=product.name,
            normalized_name=normalized_name,
            brand=product.brand,
            normalized_brand=normalized_brand,
            category=product.category,
            normalized_category=normalized_category,
            gtin=product.gtin,
            normalized_gtin=normalized_gtin,
            sku=product.sku,
            manufacturer_part_number=product.manufacturer_part_number,
            normalized_mpn=normalized_mpn,
            description=product.description,
            normalized_description=normalized_description,
            pack_quantity=product.pack_quantity,
            unit_value=unit_value,
            unit_code=unit_code,
            fingerprint=fingerprint,
        ),
        issues=tuple(issues),
    )


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    return " ".join(NON_WORDS.sub(" ", normalized).split())


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_text(value)
    return normalized or None


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None
    segments = re.split(r"\s*(?:>|/|\\|\|)\s*", value)
    normalized = " > ".join(filter(None, (normalize_text(segment) for segment in segments)))
    return normalized or None


def normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = NON_ALPHANUMERIC.sub("", unicodedata.normalize("NFKC", value).casefold())
    return normalized or None


def normalize_gtin(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) not in {8, 12, 13, 14} or not _valid_gtin_checksum(digits):
        return None
    return digits.zfill(14)


def _valid_gtin_checksum(digits: str) -> bool:
    body = digits[:-1]
    weighted_sum = sum(
        int(digit) * (3 if offset % 2 == 0 else 1) for offset, digit in enumerate(reversed(body))
    )
    expected = (10 - weighted_sum % 10) % 10
    return expected == int(digits[-1])


def normalize_unit(
    value: Decimal | None,
    code: str | None,
) -> tuple[Decimal | None, str | None]:
    if value is None or code is None:
        return value, normalize_optional_text(code)
    alias = normalize_text(code)
    mapping = UNIT_ALIASES.get(alias)
    if mapping is None:
        return value, None
    normalized_code, multiplier = mapping
    return value * multiplier, normalized_code


def build_fingerprint(values: Mapping[str, object]) -> str:
    stable_values = {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in values.items()
        if key
        in {
            "normalized_name",
            "normalized_brand",
            "normalized_category",
            "normalized_gtin",
            "normalized_mpn",
            "pack_quantity",
            "unit_value",
            "unit_code",
        }
    }
    encoded = json.dumps(stable_values, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalized_product_as_dict(product: NormalizedProduct) -> dict[str, object]:
    return asdict(product)
