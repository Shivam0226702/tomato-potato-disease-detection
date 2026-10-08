"""Database module for local plant-health scan history storage.

Uses SQLite to record diagnostic scans, estimated severity, confidence scores,
and treatment recommendations.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

# Default SQLite database path
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "plant_health.db"


def get_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Connect to SQLite database with Row factory and automatic directory creation."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that ensures connections and transactions are committed and closed cleanly."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite database and create scan_history table if it does not exist."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with db_session(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_history (
                scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                crop TEXT NOT NULL,
                disease TEXT NOT NULL,
                prediction_confidence REAL NOT NULL,
                severity TEXT NOT NULL,
                affected_area_percentage REAL,
                treatment_summary TEXT,
                notes TEXT
            );
            """
        )
        conn.commit()


def save_scan(
    crop: str,
    disease: str,
    prediction_confidence: float,
    severity: str,
    affected_area_percentage: Optional[float] = None,
    treatment_summary: str = "",
    notes: str = "",
    timestamp: Optional[str] = None,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> int:
    """Save a plant health scan result to the database.

    Args:
        crop: Crop name (e.g. 'Tomato', 'Potato').
        disease: Detected disease condition or 'Healthy'.
        prediction_confidence: Model prediction confidence percentage (0.0 to 100.0).
        severity: Estimated severity ('None (Healthy)', 'Mild', 'Moderate', 'Severe', 'Uncertain').
        affected_area_percentage: Estimated percentage of leaf discoloration, if available.
        treatment_summary: Summary of recommended actions and guidance.
        notes: Optional custom notes or observations.
        timestamp: Custom timestamp string; defaults to current local datetime.
        db_path: Path to SQLite database file.

    Returns:
        int: The newly created scan_id.
    """
    init_db(db_path)

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scan_history (
                timestamp,
                crop,
                disease,
                prediction_confidence,
                severity,
                affected_area_percentage,
                treatment_summary,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                timestamp,
                crop,
                disease,
                round(float(prediction_confidence), 2),
                severity,
                round(float(affected_area_percentage), 2) if affected_area_percentage is not None else None,
                treatment_summary,
                notes,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_scan_history(
    limit: int = 100,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve scan history ordered from newest to oldest.

    Args:
        limit: Maximum number of records to retrieve.
        db_path: Path to SQLite database file.

    Returns:
        List of dictionaries containing scan records.
    """
    init_db(db_path)

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                scan_id,
                timestamp,
                crop,
                disease,
                prediction_confidence,
                severity,
                affected_area_percentage,
                treatment_summary,
                notes
            FROM scan_history
            ORDER BY scan_id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_scan_by_id(
    scan_id: int,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Retrieve details for a single scan by its scan_id.

    Args:
        scan_id: Primary key ID of the scan.
        db_path: Path to SQLite database file.

    Returns:
        Dictionary of scan details or None if not found.
    """
    init_db(db_path)

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                scan_id,
                timestamp,
                crop,
                disease,
                prediction_confidence,
                severity,
                affected_area_percentage,
                treatment_summary,
                notes
            FROM scan_history
            WHERE scan_id = ?;
            """,
            (scan_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None


def get_scan_count(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> int:
    """Get the total count of saved scans in the database."""
    init_db(db_path)

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scan_history;")
        count = cursor.fetchone()[0]
        return int(count)


def clear_history(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> bool:
    """Clear all records from scan_history table.

    Returns:
        True if records were cleared successfully.
    """
    init_db(db_path)

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scan_history;")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='scan_history';")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        return True
