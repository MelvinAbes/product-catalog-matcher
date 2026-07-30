import pytest
from pydantic import ValidationError

from product_catalog_matcher.config import Settings


def test_matching_thresholds_are_ordered() -> None:
    with pytest.raises(ValidationError, match="review threshold must be lower"):
        Settings(auto_match_threshold=0.7, review_threshold=0.7)


def test_semantic_matching_is_disabled_by_default() -> None:
    assert Settings().semantic_matching_enabled is False
