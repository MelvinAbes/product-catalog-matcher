from pathlib import Path

from product_catalog_matcher.config import Settings
from product_catalog_matcher.evaluation import evaluate_feeds

PROJECT_ROOT = Path(__file__).parents[2]


def test_checked_in_evaluation_dataset_is_reproducible() -> None:
    report = evaluate_feeds(
        reference_file=PROJECT_ROOT / "demo/feeds/reference-products.csv",
        candidate_files=[
            PROJECT_ROOT / "demo/feeds/supplier-north.json",
            PROJECT_ROOT / "demo/feeds/supplier-central.csv",
        ],
        gold_file=PROJECT_ROOT / "evaluation/gold_pairs.csv",
        settings=Settings(environment="test"),
    )

    assert report.metrics.cases == 19
    assert report.metrics.positive_cases == 16
    assert report.metrics.negative_cases == 3
    assert report.metrics.true_positives == 14
    assert report.metrics.false_positives == 0
    assert report.metrics.false_negatives == 2
    assert report.metrics.true_negatives == 3
    assert report.metrics.review_items == 3
    assert report.metrics.precision == 1.0
    assert report.metrics.recall == 0.875
    assert report.metrics.f1 == 0.9333333333333333
