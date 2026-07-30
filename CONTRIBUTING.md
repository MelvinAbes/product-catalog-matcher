# Contributing

Contributions should preserve the separation between source evidence, normalization, candidate
generation, scoring, policy decisions, and review actions.

## Development setup

Install Python 3.12, uv, Docker, and Docker Compose. Then run:

```bash
uv sync --frozen
make check
make test-integration
```

Use `make format` before committing. Add or update tests with each behavioral change. A database
schema change requires an Alembic migration and a migration integration test.

## Matching changes

A scoring or threshold change must:

1. retain factor-level evidence;
2. increment the policy version when saved decisions could differ;
3. add focused unit cases;
4. reproduce `evaluation/results.json`; and
5. explain any metric change in the pull request.

Do not tune solely to improve the checked-in synthetic dataset. Supplier-specific evidence or a
larger independently labelled set is needed for broader calibration.

## Pull requests

Keep changes focused and describe the problem, design choice, validation performed, and any
operational impact. Before opening a pull request, run:

```bash
make check
make test-integration
make audit
docker compose config --quiet
```

Never commit `.env`, credentials, model files, private supplier records, or data without a clear
redistribution licence. Report security concerns using the process in [SECURITY.md](SECURITY.md).
