# C:/Development/Projects/Demented-Discord-Bot/data/database_manager.py

import sqlite3
import logging
import threading
import json
from pathlib import Path
from typing import List, Optional, Any

logger = logging.getLogger('demented_bot.database')

DB_FILE = Path(__file__).parent / "bot_memory.db"


class DatabaseManager:
    """
    A thread-safe manager for the SQLite database connection.
    """

    def __init__(self, db_file: Path):
        self.db_file = db_file
        self._local = threading.local()

    def get_connection(self) -> sqlite3.Connection:
        """Gets a connection from the thread-local storage, creating one if it doesn't exist."""
        if not hasattr(self._local, "connection"):
            try:
                self._local.connection = sqlite3.connect(self.db_file, check_same_thread=False)
                logger.debug(f"New DB connection created for thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.critical(f"Failed to connect to database: {e}")
                raise
        return self._local.connection

    def execute(self, sql: str, params: tuple = (), fetch: Optional[str] = None):
        """Executes a given SQL query in a thread-safe manner."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)

            if fetch == "one":
                result = cursor.fetchone()
            elif fetch == "all":
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.lastrowid
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error on query '{sql}': {e}")
            return None


# --- Singleton Instance ---
db_manager = DatabaseManager(DB_FILE)


# --- Public Functions ---

def setup_database():
    """Initializes the database and creates tables if they don't exist."""
    # Table for user facts
    user_facts_sql = """
        CREATE TABLE IF NOT EXISTS user_facts (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fact_text TEXT NOT NULL,
            added_by_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    db_manager.execute(user_facts_sql)

    # Table for user sentiment
    user_sentiment_sql = """
        CREATE TABLE IF NOT EXISTS user_sentiment (
            user_id INTEGER PRIMARY KEY,
            sentiment_score REAL NOT NULL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    db_manager.execute(user_sentiment_sql)

    # Table for OAuth2 tokens
    oauth_users_sql = """
        CREATE TABLE IF NOT EXISTS oauth_users (
            user_id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )
    """
    db_manager.execute(oauth_users_sql)

    # Table for per-server configurations
    server_configs_sql = """
        CREATE TABLE IF NOT EXISTS server_configs (
            guild_id INTEGER PRIMARY KEY,
            autonomy_channels TEXT,
            restricted_channels TEXT,
            verified_role_id INTEGER,
            unverified_role_id INTEGER
        )
    """
    db_manager.execute(server_configs_sql)

    # --- Schema Migration Logic ---
    def check_and_add_columns(table_name, columns_to_add):
        """Checks if columns exist in a table and adds them if they don't."""
        cursor = db_manager.execute(f"PRAGMA table_info({table_name})", fetch="all")
        if cursor is None:
            logger.error(f"Could not get table info for {table_name}. Migration skipped.")
            return

        existing_columns = [row[1] for row in cursor]

        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                logger.info(f"Schema migration: Adding column '{column_name}' to table '{table_name}'.")
                db_manager.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    server_configs_columns = {
        "verified_role_id": "INTEGER",
        "unverified_role_id": "INTEGER"
    }
    check_and_add_columns("server_configs", server_configs_columns)

    logger.info(f"Database initialized successfully at {DB_FILE}")


def add_user_fact(user_id: int, fact_text: str, added_by_id: int) -> bool:
    """Adds a new fact about a user to the database."""
    sql = "INSERT INTO user_facts (user_id, fact_text, added_by_id) VALUES (?, ?, ?)"
    result = db_manager.execute(sql, (user_id, fact_text, added_by_id))
    if result is not None:
        logger.info(f"Added fact for user {user_id}: '{fact_text}'")
        return True
    return False


def get_user_facts(user_id: int, limit: int = 5) -> List[str]:
    """Retrieves a list of facts about a user."""
    sql = "SELECT fact_text FROM user_facts WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?"
    rows = db_manager.execute(sql, (user_id, limit), fetch="all")
    return [row[0] for row in rows] if rows else []


def get_user_sentiment(user_id: int) -> float:
    """Retrieves the sentiment score for a user."""
    sql = "SELECT sentiment_score FROM user_sentiment WHERE user_id = ?"
    result = db_manager.execute(sql, (user_id,), fetch="one")
    return result[0] if result else 0.0


def update_user_sentiment(user_id: int, change: float):
    """Updates a user's sentiment score by a given amount."""
    insert_sql = "INSERT OR IGNORE INTO user_sentiment (user_id) VALUES (?)"
    db_manager.execute(insert_sql, (user_id,))

    update_sql = """
        UPDATE user_sentiment
        SET sentiment_score = sentiment_score + ?,
            last_updated    = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """
    db_manager.execute(update_sql, (change, user_id))
    new_score = get_user_sentiment(user_id)
    logger.info(f"Updated sentiment for user {user_id} by {change:.2f}. New score: {new_score:.2f}")


# --- Functions for OAuth2 Tokens ---

def store_oauth_tokens(user_id: int, access_token: str, refresh_token: str, expires_in: int):
    """Stores or updates a user's OAuth2 tokens in the database."""
    import time
    expires_at = int(time.time()) + expires_in
    sql = """
        INSERT INTO oauth_users (user_id, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO
        UPDATE SET
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            expires_at = excluded.expires_at
    """
    db_manager.execute(sql, (user_id, access_token, refresh_token, expires_at))
    logger.info(f"Stored OAuth tokens for user {user_id}.")


def get_oauth_tokens(user_id: int) -> Optional[dict]:
    """Retrieves a user's OAuth2 tokens from the database."""
    sql = "SELECT access_token, refresh_token, expires_at FROM oauth_users WHERE user_id = ?"
    row = db_manager.execute(sql, (user_id,), fetch="one")
    return {'access_token': row[0], 'refresh_token': row[1], 'expires_at': row[2]} if row else None


def delete_oauth_tokens(user_id: int):
    """Deletes a user's OAuth2 tokens from the database, typically on deauthorization."""
    sql = "DELETE FROM oauth_users WHERE user_id = ?"
    db_manager.execute(sql, (user_id,))
    logger.info(f"Deleted OAuth tokens for user {user_id} due to deauthorization.")


def get_all_authorized_user_ids() -> List[int]:
    """Retrieves a list of all user IDs that have stored OAuth tokens."""
    sql = "SELECT user_id FROM oauth_users"
    rows = db_manager.execute(sql, fetch="all")
    return [row[0] for row in rows] if rows else []


# --- Functions for server configurations ---

def get_server_config_value(guild_id: int, key: str) -> Optional[Any]:
    """Gets a specific configuration value for a server."""
    sql = f"SELECT {key} FROM server_configs WHERE guild_id = ?"
    result = db_manager.execute(sql, (guild_id,), fetch="one")
    return result[0] if result else None


def set_server_config_value(guild_id: int, key: str, value: Any):
    """Sets a specific configuration value for a server."""
    insert_sql = "INSERT OR IGNORE INTO server_configs (guild_id) VALUES (?)"
    db_manager.execute(insert_sql, (guild_id,))

    update_sql = f"UPDATE server_configs SET {key} = ? WHERE guild_id = ?"
    db_manager.execute(update_sql, (value, guild_id))
    logger.info(f"Updated server config for guild {guild_id}: set {key} to {value}")


def get_all_guilds_with_autonomy() -> List[int]:
    """Gets all guild IDs that have autonomy channels configured."""
    sql = "SELECT guild_id FROM server_configs WHERE autonomy_channels IS NOT NULL AND autonomy_channels != '[]'"
    results = db_manager.execute(sql, fetch="all")
    return [row[0] for row in results] if results else []