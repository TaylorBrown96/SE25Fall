"""
sqlQueries.py — SQLite helper utilities for the CSC510 Project 2 backend.

Provides simple wrappers around sqlite3 for creating connections,
executing queries, and fetching data safely.
"""

import sqlite3
from sqlite3 import Connection, Cursor
from typing import Any, Optional, Sequence


def create_connection(db_file: str) -> Connection:
    """Create and return a connection to an SQLite database.

    Args:
        db_file: Absolute or relative path to the SQLite database file.

    Returns:
        A valid sqlite3 `Connection` object.

    Raises:
        sqlite3.Error: If connection fails.
    """
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # allows dict-like row access
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(f"[DB-Error] Failed to connect to {db_file}: {e}") from e


def close_connection(conn: Connection) -> None:
    """Close an active database connection.

    Args:
        conn: The SQLite `Connection` object to close.
    """
    try:
        conn.close()
    except sqlite3.Error as e:
        print(f"[DB-Error] Failed to close connection: {e}")


def execute_query(conn: Connection, query: str, params: Sequence[Any] = ()) -> Cursor:
    """Execute a single SQL query (INSERT, UPDATE, DELETE, or SELECT).

    Args:
        conn: Open SQLite `Connection` object.
        query: SQL statement using `?` placeholders for parameters.
        params: Values to bind safely to the placeholders.

    Returns:
        The active `Cursor` on success.

    Raises:
        sqlite3.Error: If the SQL execution fails.
    """
    with conn:  # ensures commit or rollback
        cur = conn.cursor()
        cur.execute(query, params)
        return cur


def fetch_all(conn: Connection, query: str, params: Sequence[Any] = ()) -> list[tuple]:
    """Execute a query and fetch all resulting rows."""
    cur = execute_query(conn, query, params)
    return cur.fetchall()


def fetch_one(conn: Connection, query: str, params: Sequence[Any] = ()) -> Optional[tuple]:
    """Execute a query and fetch the first result row."""
    cur = execute_query(conn, query, params)
    return cur.fetchone()
