import os
from agent.memory import init_db

if __name__ == "__main__":
    db_path = os.environ.get("MEMORY_DB", "memory.db")
    init_db(db_path)
    print(f"Memory ready at {db_path}")
