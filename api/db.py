"""
DuckDB connection for SmartNews API.
Connects read-only to smartnews.duckdb.
DB_PATH must be set and the file must exist before starting the server.
"""
import logging
import os
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "smartnews.duckdb")

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        _connection = duckdb.connect(DB_PATH, read_only=True)
        logger.info("DuckDB connection opened: %s", DB_PATH)
    return _connection


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("DuckDB connection closed.")


def _run_query(sql: str, params: tuple) -> list[dict[str, Any]]:
    con = get_connection()
    result = con.execute(sql, list(params))
    if result.description is None:
        return []
    columns = [col[0] for col in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a SELECT query and return results as list of dicts."""
    try:
        return _run_query(sql, params)
    except Exception as first_err:
        logger.warning("Query failed (%s), reconnecting once...", first_err)
        close_connection()
        return _run_query(sql, params)


def execute(sql: str, params: tuple = ()) -> None:
    """Execute a write statement. (API is read-only - this is a no-op guard.)"""
    raise RuntimeError("API is read-only. Use pipeline scripts to write data.")
