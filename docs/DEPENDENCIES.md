# External dependencies and licences

The project source is licensed under Apache-2.0. Demonstration data is original and distributed
under the same licence.

| Component | Purpose | Licence consideration |
| --- | --- | --- |
| FastAPI and Pydantic | HTTP API and validation | MIT |
| SQLAlchemy and Alembic | Persistence and migrations | MIT |
| PostgreSQL | Relational data and trigram retrieval | PostgreSQL Licence |
| psycopg | PostgreSQL driver | LGPL-3.0 with exceptions |
| RapidFuzz | Token and edit similarity | MIT |
| Jinja | Server-rendered review interface | BSD-3-Clause |
| Prometheus client | Request metrics | Apache-2.0 |
| structlog | Structured application logs | Apache-2.0 or MIT |
| Sentence Transformers | Optional local semantic provider | Apache-2.0 |
| all-MiniLM-L6-v2 | Optional embedding model | Apache-2.0; downloaded separately |

The optional model is not redistributed in this repository. Its identifier is configurable and
the deployment operator is responsible for reviewing the selected model card and licence.
Runtime and development packages are resolved in `uv.lock`; the lock is audited before
publication.

