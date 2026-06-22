import os
import sqlite3
from datetime import datetime, timedelta, timezone

from src.services.snapshot.models import CostSnapshot
from src.utils.logger import logger


class SnapshotStore:
    """SQLite-backed store for historical cost report snapshots."""

    def __init__(self, db_path: str | None = None, enabled: bool | None = None):
        from src.config import SNAPSHOT_DB_PATH, SNAPSHOT_ENABLED, SNAPSHOT_RETENTION_DAYS

        self.db_path = db_path or SNAPSHOT_DB_PATH
        self.enabled = SNAPSHOT_ENABLED if enabled is None else enabled
        self.retention_days = SNAPSHOT_RETENTION_DAYS

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY,
                report_for TEXT NOT NULL,
                report_generated_on TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_report_for ON snapshots(report_for)"
        )
        conn.commit()
        return conn

    def save(self, data: dict) -> CostSnapshot | None:
        if not self.enabled:
            return None

        snapshot = CostSnapshot.from_report_data(data)
        if not snapshot.report_for:
            logger.warning("Skipping snapshot save: missing report_for")
            return None

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshots (report_for, report_generated_on, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot.report_for,
                    snapshot.report_generated_on,
                    snapshot.created_at,
                    snapshot.to_payload_json(),
                ),
            )
            conn.commit()
            snapshot.id = cursor.lastrowid

        self._purge_old()
        logger.info(f"Saved cost snapshot id={snapshot.id} report_for={snapshot.report_for}")
        return snapshot

    def get_latest(self) -> CostSnapshot | None:
        if not self.enabled:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, report_for, report_generated_on, created_at, payload_json
                FROM snapshots
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        return CostSnapshot.from_row(row) if row else None

    def get_previous(self, exclude_id: int | None = None) -> CostSnapshot | None:
        """Return the most recent snapshot, optionally excluding a just-saved id."""
        if not self.enabled:
            return None

        with self._connect() as conn:
            if exclude_id is not None:
                row = conn.execute(
                    """
                    SELECT id, report_for, report_generated_on, created_at, payload_json
                    FROM snapshots
                    WHERE id < ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (exclude_id,),
                ).fetchone()
            else:
                rows = conn.execute(
                    """
                    SELECT id, report_for, report_generated_on, created_at, payload_json
                    FROM snapshots
                    ORDER BY id DESC
                    LIMIT 2
                    """
                ).fetchall()
                row = rows[1] if len(rows) > 1 else None

        return CostSnapshot.from_row(row) if row else None

    def _purge_old(self) -> None:
        if self.retention_days <= 0:
            return

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        ).isoformat()
        with self._connect() as conn:
            deleted = conn.execute(
                "DELETE FROM snapshots WHERE created_at < ?", (cutoff,)
            ).rowcount
            conn.commit()
        if deleted:
            logger.info(f"Purged {deleted} snapshot(s) older than {self.retention_days} days")
