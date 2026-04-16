from __future__ import annotations

import uvicorn

from backend.db import Database
from backend.entrypoints.api.main import create_app
from backend.shared.config import load_config


def main() -> None:
    config = load_config()
    database = Database(config.database_url)
    app = create_app(config, database)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
