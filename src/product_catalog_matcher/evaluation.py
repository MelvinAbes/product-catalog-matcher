import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import MatchDecision, RecordStatus
from product_catalog_matcher.ingestion.parser import parse_feed
from product_catalog_matcher.matching.policy import classify_best_candidate
from product_catalog_matcher.matching.scoring import POLICY_VERSION, score_product_pair
from product_catalog_matcher.normalization.products import NormalizedProduct, normalize_product
from product_catalog_matcher.persistence.models import CanonicalProduct, SupplierProduct


@dataclass(frozen=True)
class EvaluationPrediction:
    candidate_id: str
    gold_reference_id: str | None
    top_reference_id: str | None
    automated_reference_id: str | None
    decision: str
    score: float | None
    winning_margin: float | None
    correct: bool


@dataclass(frozen=True)
class EvaluationMetrics:
    cases: int
    positive_cases: int
    negative_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    review_items: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EvaluationReport:
    policy_version: str
    semantic_matching_enabled: bool
    metrics: EvaluationMetrics
    predictions: tuple[EvaluationPrediction, ...]


def evaluate_feeds(
    *,
    reference_file: Path,
    candidate_files: list[Path],
    gold_file: Path,
    settings: Settings,
) -> EvaluationReport:
    references = _load_normalized_products(reference_file, settings)
    candidates = [
        product
        for candidate_file in candidate_files
        for product in _load_normalized_products(candidate_file, settings)
    ]
    gold = _load_gold(gold_file)
    candidate_ids = {candidate.source_record_id for candidate in candidates}
    if set(gold) != candidate_ids:
        missing_labels = sorted(candidate_ids - set(gold))
        missing_products = sorted(set(gold) - candidate_ids)
        raise ValueError(
            "Evaluation labels and candidate feeds differ: "
            f"unlabelled={missing_labels}, absent={missing_products}"
        )

    canonical_by_source_id = {
        product.source_record_id: _canonical_product(product) for product in references
    }
    reference_by_uuid = {
        product.id: source_id for source_id, product in canonical_by_source_id.items()
    }
    predictions: list[EvaluationPrediction] = []
    for candidate in candidates:
        source = _supplier_product(candidate)
        ranked = sorted(
            (score_product_pair(source, target) for target in canonical_by_source_id.values()),
            key=lambda result: result.score,
            reverse=True,
        )
        policy = classify_best_candidate(
            ranked,
            auto_match_threshold=settings.auto_match_threshold,
            review_threshold=settings.review_threshold,
            minimum_winning_margin=settings.minimum_winning_margin,
        )
        top_reference_id = reference_by_uuid[ranked[0].canonical_product.id] if ranked else None
        automated_reference_id = (
            top_reference_id if policy.decision is MatchDecision.AUTO_MATCH else None
        )
        gold_reference_id = gold[candidate.source_record_id]
        predictions.append(
            EvaluationPrediction(
                candidate_id=candidate.source_record_id,
                gold_reference_id=gold_reference_id,
                top_reference_id=top_reference_id,
                automated_reference_id=automated_reference_id,
                decision=policy.decision.value,
                score=ranked[0].score if ranked else None,
                winning_margin=policy.winning_margin,
                correct=automated_reference_id == gold_reference_id,
            )
        )

    return EvaluationReport(
        policy_version=POLICY_VERSION,
        semantic_matching_enabled=False,
        metrics=_calculate_metrics(predictions),
        predictions=tuple(predictions),
    )


def _load_normalized_products(path: Path, settings: Settings) -> list[NormalizedProduct]:
    content = path.read_bytes()
    parsed = parse_feed(
        file_name=path.name,
        content=content,
        max_bytes=settings.upload_max_bytes,
        max_rows=settings.import_max_rows,
    )
    products: list[NormalizedProduct] = []
    for row in parsed.rows:
        if row.product is None:
            issues = ", ".join(issue.code for issue in row.issues)
            raise ValueError(f"{path}:{row.row_number} is invalid: {issues}")
        products.append(normalize_product(row.product, row_number=row.row_number).product)
    return products


def _load_gold(path: Path) -> dict[str, str | None]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["candidate_id", "reference_id"]:
            raise ValueError("Gold labels must contain candidate_id and reference_id columns.")
        labels: dict[str, str | None] = {}
        for row in reader:
            candidate_id = row["candidate_id"].strip()
            if candidate_id in labels:
                raise ValueError(f"Duplicate gold label for {candidate_id}.")
            labels[candidate_id] = row["reference_id"].strip() or None
    return labels


def _canonical_product(product: NormalizedProduct) -> CanonicalProduct:
    return CanonicalProduct(
        id=uuid4(),
        name=product.name,
        normalized_name=product.normalized_name,
        brand=product.brand,
        normalized_brand=product.normalized_brand,
        category=product.category,
        normalized_category=product.normalized_category,
        gtin=product.normalized_gtin,
        manufacturer_part_number=product.manufacturer_part_number,
        normalized_mpn=product.normalized_mpn,
        pack_quantity=product.pack_quantity,
        unit_value=product.unit_value,
        unit_code=product.unit_code,
    )


def _supplier_product(product: NormalizedProduct) -> SupplierProduct:
    return SupplierProduct(
        id=uuid4(),
        supplier_id=uuid4(),
        import_batch_id=uuid4(),
        source_record_id=product.source_record_id,
        source_row_number=1,
        record_status=RecordStatus.VALID,
        raw_data={},
        name=product.name,
        normalized_name=product.normalized_name,
        brand=product.brand,
        normalized_brand=product.normalized_brand,
        category=product.category,
        normalized_category=product.normalized_category,
        gtin=product.gtin,
        normalized_gtin=product.normalized_gtin,
        sku=product.sku,
        manufacturer_part_number=product.manufacturer_part_number,
        normalized_mpn=product.normalized_mpn,
        description=product.description,
        normalized_description=product.normalized_description,
        pack_quantity=product.pack_quantity,
        unit_value=product.unit_value,
        unit_code=product.unit_code,
        fingerprint=product.fingerprint,
    )


def _calculate_metrics(
    predictions: list[EvaluationPrediction],
) -> EvaluationMetrics:
    true_positives = false_positives = false_negatives = true_negatives = 0
    for prediction in predictions:
        if prediction.gold_reference_id is not None:
            if prediction.automated_reference_id == prediction.gold_reference_id:
                true_positives += 1
            else:
                false_negatives += 1
                if prediction.automated_reference_id is not None:
                    false_positives += 1
        elif prediction.automated_reference_id is None:
            true_negatives += 1
        else:
            false_positives += 1

    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    return EvaluationMetrics(
        cases=len(predictions),
        positive_cases=sum(item.gold_reference_id is not None for item in predictions),
        negative_cases=sum(item.gold_reference_id is None for item in predictions),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        review_items=sum(item.decision == MatchDecision.REVIEW.value for item in predictions),
        precision=precision,
        recall=recall,
        f1=_safe_divide(2 * precision * recall, precision + recall),
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def report_as_dict(report: EvaluationReport) -> dict[str, Any]:
    return asdict(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic catalog matching.")
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    report = evaluate_feeds(
        reference_file=arguments.reference,
        candidate_files=arguments.candidate,
        gold_file=arguments.gold,
        settings=Settings(environment="test"),
    )
    document = json.dumps(report_as_dict(report), indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(document, encoding="utf-8")
    else:
        sys.stdout.write(document)


if __name__ == "__main__":
    main()
