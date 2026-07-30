from decimal import Decimal

from product_catalog_matcher.ingestion.schemas import SupplierProductInput
from product_catalog_matcher.normalization.products import (
    normalize_category,
    normalize_gtin,
    normalize_product,
    normalize_text,
)


def test_text_and_category_normalization_preserve_meaningful_tokens() -> None:
    assert normalize_text("  Café & Tea—Set ") == "café and tea set"
    assert normalize_category("Home / Kitchen > Drinkware") == "home > kitchen > drinkware"


def test_valid_gtins_are_padded_to_a_common_representation() -> None:
    assert normalize_gtin("4006 3813 3393 1") == "04006381333931"
    assert normalize_gtin("036000291452") == "00036000291452"


def test_invalid_gtin_is_kept_as_source_evidence_but_not_used_for_matching() -> None:
    result = normalize_product(
        SupplierProductInput(
            source_record_id="A-1",
            name="Travel Mug",
            gtin="4006381333932",
        ),
        row_number=2,
    )

    assert result.product.gtin == "4006381333932"
    assert result.product.normalized_gtin is None
    assert result.issues[0].code == "invalid_gtin"


def test_units_are_converted_to_comparable_base_units() -> None:
    result = normalize_product(
        SupplierProductInput(
            source_record_id="A-1",
            name="Arabica Coffee",
            unit_value=Decimal("1"),
            unit_code="kg",
        ),
        row_number=2,
    )

    assert result.product.unit_value == Decimal("1000")
    assert result.product.unit_code == "g"


def test_fingerprint_is_stable_across_formatting_differences() -> None:
    first = normalize_product(
        SupplierProductInput(
            source_record_id="A-1",
            name="Travel-Mug",
            brand="Kite Works",
            manufacturer_part_number="KW TM-20",
        ),
        row_number=2,
    )
    second = normalize_product(
        SupplierProductInput(
            source_record_id="A-2",
            name="travel mug",
            brand="kite   works",
            manufacturer_part_number="kw-tm20",
        ),
        row_number=3,
    )

    assert first.product.fingerprint == second.product.fingerprint
