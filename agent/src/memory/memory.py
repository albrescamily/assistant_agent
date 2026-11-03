import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

SCHEMA = Path(__file__).parent / "sqlite.sql"


@contextmanager
def connect(db_path):
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path, schema_path=SCHEMA):
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))


class Memory:
    def __init__(self, db_path, session_id):
        self.db_path = db_path
        self.session_id = session_id

    def load_history(self, limit=20):
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id
                """,
                (self.session_id, limit),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in rows]

    def save_exchange(self, user_message, reply):
        # local time (container TZ), instead of SQLite's CURRENT_TIMESTAMP, which is always UTC
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with connect(self.db_path) as conn:
            conn.executemany(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                [
                    (self.session_id, "user", user_message, now),
                    (self.session_id, "assistant", reply, now),
                ],
            )
