from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SupplierProductInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    source_record_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=500)
    brand: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=300)
    gtin: str | None = Field(default=None, max_length=40)
    sku: str | None = Field(default=None, max_length=160)
    manufacturer_part_number: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5_000)
    pack_quantity: Decimal | None = Field(default=None, gt=0)
    unit_value: Decimal | None = Field(default=None, gt=0)
    unit_code: str | None = Field(default=None, max_length=20)

    @field_validator(
        "brand",
        "category",
        "gtin",
        "sku",
        "manufacturer_part_number",
        "description",
        "unit_code",
        mode="before",
    )
    @classmethod
    def empty_strings_are_missing(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value
