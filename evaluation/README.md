# Matching and decision evaluation

The dataset contains 17 reference products and 19 supplier records. Sixteen supplier records
have a known equivalent; three are deliberately related but non-equivalent products. Every
record is fictional and covered by `demo/DATA_LICENSE.md`.

The metric treats only `auto_match` decisions as positive predictions. A correct suggestion
routed to review remains a false negative for automation recall because no catalog link is
created without a reviewer. An automatic link to a wrong reference counts as both a false
positive and a false negative.

Run the evaluation with:

```bash
uv run catalog-evaluate \
  --reference demo/feeds/reference-products.csv \
  --candidate demo/feeds/supplier-north.json \
  --candidate demo/feeds/supplier-central.csv \
  --gold evaluation/gold_pairs.csv \
  --output evaluation/results.json
```

The checked-in `results.json` was reproduced with the locked dependencies and default
deterministic policy:

| Metric | Result |
| --- | ---: |
| Cases | 19 |
| True positives | 14 |
| False positives | 0 |
| False negatives | 2 |
| True negatives | 3 |
| Precision | 1.000 |
| Recall | 0.875 |
| F1 | 0.933 |
| Routed to review | 3 |

This is a small regression dataset, not a production benchmark. It checks known normalization,
identifier, ambiguity, and near-neighbour cases. Supplier-specific drift and a larger
independently labelled corpus are required before tuning production thresholds.
