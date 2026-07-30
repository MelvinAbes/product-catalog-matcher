# Operations

## Configuration

Settings use the `PCM_` prefix and are loaded from environment variables or a local `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PCM_DATABASE_URL` | local PostgreSQL URL | SQLAlchemy connection string |
| `PCM_APP_PORT` | `8000` in Compose | Published application port |
| `PCM_DB_PORT` | `5432` in Compose | Published database port |
| `PCM_UPLOAD_MAX_BYTES` | `5242880` | Maximum uploaded feed size |
| `PCM_IMPORT_MAX_ROWS` | `5000` | Maximum parsed data rows |
| `PCM_AUTO_MATCH_THRESHOLD` | `0.80` | Automatic-match confidence |
| `PCM_REVIEW_THRESHOLD` | `0.65` | Minimum review confidence |
| `PCM_MINIMUM_WINNING_MARGIN` | `0.08` | Required automatic-match separation |
| `PCM_CANDIDATE_SIMILARITY_FLOOR` | `0.25` | Minimum trigram candidate similarity |
| `PCM_CANDIDATE_LIMIT` | `20` | Maximum candidates scored per source record |
| `PCM_PROPOSAL_LIMIT` | `3` | Ranked proposals stored per source record |
| `PCM_LOG_FORMAT` | `json` | `json` or developer-oriented `console` logs |
| `PCM_SEMANTIC_MATCHING_ENABLED` | `false` | Enable the optional local scorer |
| `PCM_SEMANTIC_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local model identifier |

`POSTGRES_PASSWORD` is required by Compose. `.env.example` contains a development placeholder;
choose a different value for any shared environment.

## Database lifecycle

The application container runs `alembic upgrade head` before starting the HTTP server. Host-side
migrations can be applied with `make migrate`. PostgreSQL persists in the `catalog-data` named
volume.

`docker compose down` keeps the volume. `docker compose down --volumes` permanently removes the
local catalog and review history, so export data first if it matters.

The project does not automate backups or point-in-time recovery. A non-local deployment needs a
tested backup, restore, retention, and schema-migration procedure.

## Health

- `/health/live` reports whether the HTTP process is alive.
- `/health/ready` checks a PostgreSQL query and returns `503` when the database is unavailable.
- The Compose health check uses readiness before marking the application healthy.

## Logs and request correlation

Production logs are JSON and written to standard output. Every HTTP request receives an
`X-Request-ID`; a valid incoming ID is preserved, otherwise a new one is generated. Request
completion logs include method, path, status, and elapsed time. Inspect recent container output
with:

```bash
make logs
```

Do not log feed bodies, raw supplier records, credentials, or review-session identifiers.

## Metrics

`/metrics` exposes Prometheus text format with request totals and duration histograms labelled by
method, route template, and status. Unmatched paths use a bounded label rather than the raw URL
to avoid unbounded cardinality.

The repository does not include alert rules. A real deployment should alert on readiness
failures, sustained server errors, import failures, and review-queue growth using thresholds
derived from its own traffic.

## Container posture

The application runs as UID `10001`, drops Linux capabilities, prevents privilege escalation,
and uses a read-only root filesystem with a bounded temporary filesystem. PostgreSQL also starts
as its unprivileged service user. Base images are pinned by digest and scanned in CI. These
controls reduce container risk but do not replace network policy, TLS termination,
authentication, or a managed secrets store.
