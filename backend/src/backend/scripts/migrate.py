from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import asyncpg


async def _run(database_url: str, migrations_dir: Path) -> None:
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS _backend_migrations (
              migration_id text PRIMARY KEY,
              applied_at timestamptz NOT NULL DEFAULT now()
            );
            """
        )

        applied = await connection.fetch("SELECT migration_id FROM _backend_migrations")
        applied_ids = {row["migration_id"] for row in applied}

        for file_path in sorted(migrations_dir.glob("*.sql")):
            migration_id = file_path.name
            if migration_id in applied_ids:
                continue
            sql = file_path.read_text()
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO _backend_migrations (migration_id) VALUES ($1)",
                    migration_id,
                )
    finally:
        await connection.close()


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
