from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from pathlib import Path


class AtomicIDManager:
    """A database manager for managing thread IDs.

    This was written by Claude, and I fixed it up with feedback from Ruff and Flake8.
    Maybe one day the app logic database will require something fancier, but this gets the job done now.

    As you can see from the conversation with Claude, this was quite a simple task for it:
    https://claude.ai/share/227d08ff-96a3-495a-9f56-509a1fd528f7
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database manager."""
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize the database and create the table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrent access
            await db.execute("PRAGMA journal_mode=WAL")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS claimed_ids (
                    id INTEGER PRIMARY KEY
                )
            """)
            await db.commit()

    async def claim_next_id(self) -> int:
        """Atomically find the max id, increment it, and claim it. Returns the newly claimed ID.

        This operation is atomic and multiprocess-safe because:
        1. SQLite serializes writes by default
        2. We use IMMEDIATE transaction to acquire write lock immediately
        3. The entire operation happens in a single transaction
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Start an IMMEDIATE transaction to get write lock right away
            await db.execute("BEGIN IMMEDIATE")

            try:
                # Find the current max ID
                async with db.execute("SELECT MAX(id) FROM claimed_ids") as cursor:
                    row = await cursor.fetchone()
                    max_id = row[0] if row is not None and row[0] is not None else 0

                # Calculate next ID
                next_id = max_id + 1

                # Insert the new ID
                await db.execute("INSERT INTO claimed_ids (id) VALUES (?)", (next_id,))

                # Commit the transaction
                await db.commit()

            except Exception:
                await db.rollback()
                raise

            else:
                return next_id

    async def get_all_claimed_ids(self) -> list[int]:
        """Retrieve all claimed IDs."""
        async with (
            aiosqlite.connect(self.db_path) as db,
            db.execute("SELECT id FROM claimed_ids ORDER BY id") as cursor,
        ):
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_count(self) -> int:
        """Get the total number of claimed IDs."""
        async with aiosqlite.connect(self.db_path) as db, db.execute("SELECT COUNT(*) FROM claimed_ids") as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise ValueError("A SQL COUNT query should always return at least one row")  # noqa: EM101, TRY003
            return row[0]
