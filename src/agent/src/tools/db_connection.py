import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

#postgreSQL
@contextmanager
def connect():
    conn = psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],  # agent_ro: only has SELECT permission
        password=os.environ["DB_PASSWORD"],
        row_factory=dict_row,  # each row comes back as a dict: {"order_id": 1, "status": "shipped"}
    )
    conn.read_only = True  # second guard: every transaction is read-only, even if the user had more rights
    try:
        with conn:
            yield conn
    finally:
        conn.close()

