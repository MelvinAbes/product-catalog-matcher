import uvicorn
from alembic import command
from alembic.config import Config

from product_catalog_matcher.config import get_settings


def main() -> None:
    settings = get_settings()
    command.upgrade(Config("alembic.ini"), "head")
    uvicorn.run(
        "product_catalog_matcher.main:app",
        host=settings.server_host,
        port=settings.server_port,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
