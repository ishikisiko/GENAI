from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _run(database_url: str, migrations_dir: Path) -> None:
    if "postgresql+asyncpg" not in database_url and "postgresql://" in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, future=True)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS _backend_migrations (
                  migration_id text PRIMARY KEY,
                  applied_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )
        )

        applied = await connection.execute(text("SELECT migration_id FROM _backend_migrations"))
        applied_ids = {row[0] for row in applied.all()}

        for file_path in sorted(migrations_dir.glob("*.sql")):
            migration_id = file_path.name
            if migration_id in applied_ids:
                continue
            sql = file_path.read_text()
            await connection.execute(text(sql))
            await connection.execute(
                text(
                    "INSERT INTO _backend_migrations (migration_id) VALUES (:migration_id)"
                ),
                {"migration_id": migration_id},
            )
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply backend SQL migrations.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--migrations-dir",
        required=True,
        help="Directory containing .sql migration files.",
    )
    args = parser.parse_args()

    asyncio.run(_run(args.database_url, Path(args.migrations_dir)))


if __name__ == "__main__":
    main()
