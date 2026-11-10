"""
Database Connection and Initialization Manager for Life Insurance Data Warehouse.
Supports both SQLite 3 and DuckDB.
"""

import os
import sqlite3
import duckdb
from typing import Union
from .schema import SQL_DDL

class DatabaseManager:
    def __init__(self, db_path: str = "life_insurance.db", engine: str = "sqlite"):
        self.db_path = db_path
        self.engine = engine.lower()
        self._conn = None

    def connect(self):
        """Establishes connection to the target database engine."""
        if self.engine == "sqlite":
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
            # Row factory for dictionary-like access
            self._conn.row_factory = sqlite3.Row
        elif self.engine == "duckdb":
            self._conn = duckdb.connect(self.db_path)
        else:
            raise ValueError(f"Unsupported database engine: {self.engine}. Choose 'sqlite' or 'duckdb'.")
        return self._conn

    @property
    def connection(self):
        if self._conn is None:
            return self.connect()
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init_schema(self, force: bool = False):
        """Initializes database schema, executing all ANSI SQL DDL statements and Views."""
        conn = self.connection
        if force:
            # If force is requested and SQLite, drop views and tables cleanly
            if self.engine == "sqlite":
                cursor = conn.cursor()
                # Disable foreign keys while dropping
                cursor.execute("PRAGMA foreign_keys = OFF;")
                views = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
                for v in views:
                    cursor.execute(f"DROP VIEW IF EXISTS {v}")
                tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
                for t in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {t}")
                conn.commit()
                cursor.execute("PRAGMA foreign_keys = ON;")

        if self.engine == "sqlite":
            cursor = conn.cursor()
            statements = [s.strip() for s in SQL_DDL.split(";") if s.strip()]
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e).lower():
                        continue
                    raise
            conn.commit()
        elif self.engine == "duckdb":
            statements = [s.strip() for s in SQL_DDL.split(";") if s.strip()]
            for stmt in statements:
                try:
                    conn.execute(stmt)
                except Exception as e:
                    if "already exists" in str(e).lower():
                        continue
                    raise

    def execute(self, sql: str, params: tuple = ()):
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: list):
        return self.connection.executemany(sql, seq_of_params)

    def commit(self):
        if self.engine == "sqlite":
            self.connection.commit()

    def rollback(self):
        if self.engine == "sqlite":
            self.connection.rollback()
