#!/usr/bin/env bash
set -euo pipefail

api_url="${PCM_API_URL:-http://localhost:8000}"

for command_name in curl jq; do
  if ! command -v "${command_name}" >/dev/null; then
    echo "${command_name} is required to load the demonstration data." >&2
    exit 1
  fi
done

post_json() {
  curl --silent --show-error --fail-with-body \
    -H "Content-Type: application/json" \
    -d "$2" \
    "${api_url}$1"
}

reference_supplier_id="$(
  post_json "/api/v1/suppliers" \
    '{"code":"reference-catalog","name":"Reference Catalog"}' | jq -er '.id'
)"
north_supplier_id="$(
  post_json "/api/v1/suppliers" \
    '{"code":"supplier-north","name":"Supplier North"}' | jq -er '.id'
)"
central_supplier_id="$(
  post_json "/api/v1/suppliers" \
    '{"code":"supplier-central","name":"Supplier Central"}' | jq -er '.id'
)"

reference_batch_id="$(
  curl --silent --show-error --fail-with-body \
    -F "supplier_id=${reference_supplier_id}" \
    -F "role=reference" \
    -F "file=@demo/feeds/reference-products.csv;type=text/csv" \
    "${api_url}/api/v1/imports" | jq -er '.id'
)"
north_batch_id="$(
  curl --silent --show-error --fail-with-body \
    -F "supplier_id=${north_supplier_id}" \
    -F "role=candidate" \
    -F "file=@demo/feeds/supplier-north.json;type=application/json" \
    "${api_url}/api/v1/imports" | jq -er '.id'
)"
central_batch_id="$(
  curl --silent --show-error --fail-with-body \
    -F "supplier_id=${central_supplier_id}" \
    -F "role=candidate" \
    -F "file=@demo/feeds/supplier-central.csv;type=text/csv" \
    "${api_url}/api/v1/imports" | jq -er '.id'
)"

north_result="$(
  curl --silent --show-error --fail-with-body \
    -X POST "${api_url}/api/v1/imports/${north_batch_id}/match"
)"
central_result="$(
  curl --silent --show-error --fail-with-body \
    -X POST "${api_url}/api/v1/imports/${central_batch_id}/match"
)"
quality="$(
  curl --silent --show-error --fail-with-body \
    "${api_url}/api/v1/imports/${central_batch_id}/quality"
)"
reviews="$(
  curl --silent --show-error --fail-with-body "${api_url}/api/v1/reviews"
)"

curl --silent --show-error --fail "${api_url}/" >/dev/null
curl --silent --show-error --fail "${api_url}/metrics" >/dev/null

jq -n \
  --arg reference_batch_id "${reference_batch_id}" \
  --argjson north "${north_result}" \
  --argjson central "${central_result}" \
  --argjson quality "${quality}" \
  --argjson review_count "$(jq 'length' <<<"${reviews}")" \
  '{
    reference_batch_id: $reference_batch_id,
    candidate_batches: [$north, $central],
    central_quality: {
      total_rows: $quality.total_rows,
      issue_count: $quality.issue_count,
      duplicate_rows: $quality.duplicate_rows
    },
    open_reviews: $review_count
  }'

