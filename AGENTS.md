# Repository working agreement

- Keep the matching pipeline deterministic when semantic matching is disabled.
- Preserve raw supplier values; normalization produces separate derived fields.
- Store a score explanation and policy version for every match proposal.
- Treat migrations as immutable after they have been shared.
- Add or update evaluation cases when matching weights or thresholds change.
- Use precise domain names and keep functions focused on one pipeline stage.
- Comments should capture constraints or non-obvious decisions.
- Never commit credentials, local environment files, personal data, or proprietary supplier feeds.
- Run formatting, linting, typing, tests, dependency checks, and secret scanning before publication.
- Keep optional model integrations disabled by default and isolated behind the semantic scorer boundary.

