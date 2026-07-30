import json

import pytest

from product_catalog_matcher.ingestion.parser import FeedStructureError, parse_feed


def test_csv_aliases_are_mapped_to_canonical_fields() -> None:
    content = (
        b"product_id;title;manufacturer;category_path;ean;model_number;amount;unit\n"
        b"A-100;Arabica Coffee Beans;Northwind Roasters;Grocery > Coffee;"
        b"4006381333931;NR-AR-1;1;kg\n"
    )

    result = parse_feed(
        file_name="supplier.csv",
        content=content,
        max_bytes=10_000,
        max_rows=10,
    )

    assert result.format == "csv"
    assert result.rows[0].product is not None
    assert result.rows[0].product.source_record_id == "A-100"
    assert result.rows[0].product.manufacturer_part_number == "NR-AR-1"


def test_json_products_wrapper_is_supported() -> None:
    content = json.dumps(
        {
            "products": [
                {
                    "item_id": "B-200",
                    "product_name": "Insulated Travel Mug",
                    "maker": "Kite Works",
                }
            ]
        }
    ).encode()

    result = parse_feed(
        file_name="supplier.json",
        content=content,
        max_bytes=10_000,
        max_rows=10,
    )

    assert result.rows[0].product is not None
    assert result.rows[0].product.brand == "Kite Works"


def test_invalid_rows_return_field_level_issues() -> None:
    result = parse_feed(
        file_name="supplier.csv",
        content=b"id,name\nA-1,\n",
        max_bytes=10_000,
        max_rows=10,
    )

    assert result.rows[0].product is None
    assert result.rows[0].issues[0].code == "invalid_name"


@pytest.mark.parametrize(
    ("file_name", "content", "code"),
    [
        ("supplier.xml", b"<products/>", "unsupported_format"),
        ("supplier.json", b"{}", "invalid_json_shape"),
        ("supplier.csv", b"id,id,name\n1,2,Product\n", "duplicate_header"),
        ("supplier.csv", b"id,name\n1,Product\n", "file_too_large"),
    ],
)
def test_structural_errors_are_explicit(file_name: str, content: bytes, code: str) -> None:
    with pytest.raises(FeedStructureError) as error:
        parse_feed(
            file_name=file_name,
            content=content,
            max_bytes=10 if code == "file_too_large" else 10_000,
            max_rows=10,
        )

    assert error.value.code == code


def test_row_limit_is_enforced_after_parsing() -> None:
    with pytest.raises(FeedStructureError, match="configured limit") as error:
        parse_feed(
            file_name="supplier.csv",
            content=b"id,name\n1,One\n2,Two\n",
            max_bytes=10_000,
            max_rows=1,
        )

    assert error.value.code == "too_many_rows"
