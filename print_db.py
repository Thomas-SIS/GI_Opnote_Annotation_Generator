"""Print all text content stored in the project's SQLite database.

This script discovers all user tables, finds text-like columns, and prints
non-empty text values to stdout. It reuses the same `DATABASE_DIR` behavior
as the application via `utils.database_init.AsyncDatabaseInitializer`.

Run: set the `DATABASE_DIR` environment variable (or point it to the
      repository `database` folder) and run `python print_db.py`.
"""
import asyncio
from typing import List

import aiosqlite

from utils.database_init import AsyncDatabaseInitializer


def _is_text_type(col_type: str) -> bool:
    """Return True if the SQLite column type string represents text.

    Args:
        col_type: The type string returned by PRAGMA table_info (may be empty).

    Returns:
        True for types typically used to store text.
    """
    t = (col_type or "").upper()
    return any(x in t for x in ("CHAR", "CLOB", "TEXT", "VARCHAR"))


async def _print_table_text(conn: aiosqlite.Connection, table: str) -> None:
    """Print all non-empty text fields for rows in a given table.

    Args:
        conn: An aiosqlite connection.
        table: Table name to inspect and print.
    """
    cur = await conn.execute(f"PRAGMA table_info({table})")
    cols = await cur.fetchall()
    text_cols: List[str] = [c[1] for c in cols if _is_text_type(c[2])]
    if not text_cols:
        return

    cols_sql = ", ".join(["rowid"] + text_cols)
    cur = await conn.execute(f"SELECT {cols_sql} FROM {table}")
    rows = await cur.fetchall()

    if not rows:
        return

    print(f"Table: {table}")
    for row in rows:
        rowid = row[0]
        entries = []
        for idx, col in enumerate(text_cols, start=1):
            val = row[idx]
            if val is None:
                continue
            s = str(val).strip()
            if not s:
                continue
            entries.append(f"{col}={s!r}")
        if entries:
            print(f"  rowid={rowid}: " + "; ".join(entries))
    print()


async def main() -> None:
    """Ensure DB exists and print text content from all user tables."""
    initializer = AsyncDatabaseInitializer()
    async with initializer.connection() as conn:
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [r[0] for r in await cur.fetchall()]
        for table in tables:
            await _print_table_text(conn, table)


if __name__ == "__main__":
    asyncio.run(main())
