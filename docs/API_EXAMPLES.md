# API examples

The interactive OpenAPI documentation is served at <http://localhost:8000/api/docs>. All
examples assume the Compose stack is healthy and start with:

```bash
api_url="http://localhost:8000"
```

## Register suppliers

```bash
reference_supplier_id="$(
  curl --silent --fail-with-body \
    -H "Content-Type: application/json" \
    -d '{"code":"reference-catalog","name":"Reference Catalog"}' \
    "${api_url}/api/v1/suppliers" | jq -r '.id'
)"

candidate_supplier_id="$(
  curl --silent --fail-with-body \
    -H "Content-Type: application/json" \
    -d '{"code":"supplier-north","name":"Supplier North"}' \
    "${api_url}/api/v1/suppliers" | jq -r '.id'
)"
```

Each response contains a generated UUID and timestamp:

```json
{
  "id": "<supplier UUID>",
  "code": "supplier-north",
  "name": "Supplier North",
  "created_at": "<UTC timestamp>"
}
```

## Import the reference catalog

```bash
reference_batch_id="$(
  curl --silent --fail-with-body \
    -F "supplier_id=${reference_supplier_id}" \
    -F "role=reference" \
    -F "file=@demo/feeds/reference-products.csv;type=text/csv" \
    "${api_url}/api/v1/imports" | jq -r '.id'
)"
```

A completed import records content identity and quality counts. The demo reference response has
17 accepted rows, no rejected rows, and no issues.

## Import and match a supplier feed

```bash
candidate_batch_id="$(
  curl --silent --fail-with-body \
    -F "supplier_id=${candidate_supplier_id}" \
    -F "role=candidate" \
    -F "file=@demo/feeds/supplier-north.json;type=application/json" \
    "${api_url}/api/v1/imports" | jq -r '.id'
)"

curl --silent --fail-with-body -X POST \
  "${api_url}/api/v1/imports/${candidate_batch_id}/match" | jq
```

The locked demo policy returns:

```json
{
  "batch_id": "<candidate batch UUID>",
  "processed": 10,
  "auto_matches": 6,
  "review_items": 2,
  "no_matches": 2,
  "policy_version": "deterministic-v1",
  "semantic_used": false
}
```

Matching a batch is intentionally single-use. Repeating the request returns `409 Conflict` with
an `application/problem+json` body.

## Inspect normalized data and quality

```bash
curl --silent --fail-with-body \
  "${api_url}/api/v1/imports/${candidate_batch_id}/products" | jq

curl --silent --fail-with-body \
  "${api_url}/api/v1/imports/${candidate_batch_id}/issues" | jq

curl --silent --fail-with-body \
  "${api_url}/api/v1/imports/${candidate_batch_id}/quality" | jq
```

The product response exposes source and normalized values separately. The quality response
contains accepted, rejected, and duplicate counts; completeness ratios; and issue counts grouped
by code and severity.

## Search the canonical catalog

```bash
curl --silent --get --fail-with-body \
  --data-urlencode "query=usb charger" \
  --data "limit=10" \
  "${api_url}/api/v1/catalog" | jq
```

## Review an uncertain proposal

```bash
proposal_id="$(
  curl --silent --fail-with-body "${api_url}/api/v1/reviews?limit=1" |
    jq -r '.[0].proposal_id'
)"

curl --silent --fail-with-body \
  "${api_url}/api/v1/reviews/${proposal_id}" | jq
```

The detail includes source and target records, confidence, winning margin, policy version, and
the raw score, weight, contribution, and evidence for every active factor.

Accept the proposed target:

```bash
curl --silent --fail-with-body \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accepted",
    "reviewer": "catalog-reviewer",
    "rationale": "Brand, model, capacity, and normalized title agree."
  }' \
  "${api_url}/api/v1/reviews/${proposal_id}/decisions" | jq
```

Use `rejected` when no catalog target is equivalent. Use `reassigned` with a
`canonical_product_id` when a different target is correct. Decisions are append-only, and an
already resolved proposal returns `409 Conflict`.

## Health and metrics

```bash
curl --silent --fail "${api_url}/health/live" | jq
curl --silent --fail "${api_url}/health/ready" | jq
curl --silent --fail "${api_url}/metrics" | grep catalog_matcher_http_requests_total
```

Liveness indicates that the process can serve HTTP. Readiness returns `503` until PostgreSQL is
reachable.

## Problem response

Domain errors use `application/problem+json`:

```json
{
  "type": "urn:product-catalog-matcher:error:duplicate_feed",
  "title": "Duplicate supplier feed",
  "status": 409,
  "detail": "This supplier feed has already been imported."
}
```

Validation failures from the HTTP boundary use FastAPI's structured `422` response.
