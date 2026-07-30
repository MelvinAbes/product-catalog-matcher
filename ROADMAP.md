# Roadmap

The current release covers bounded supplier imports, deterministic matching, manual review,
quality reports, evaluation, observability, and a containerized local workflow.

## Next

- Move imports and matching to durable background jobs with progress resources
- Add supplier-specific normalization aliases and versioned matching profiles
- Add authentication, reviewer roles, and tenant-scoped data access

## Later

- Measure reviewer agreement and threshold performance over time
- Support catalog merge and split corrections without losing history
- Add drift reports for identifier completeness, category changes, and score distributions
- Evaluate approximate nearest-neighbour semantic candidate generation on a larger labelled set

Each item requires acceptance criteria and representative tests before implementation.
