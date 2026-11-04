import json
import os
import re
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))


def log_turn(session_id, request, behavior, reply):
    # one file per session, one JSON line per message: what the customer asked, what the model did, what it answered
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^\w-]", "_", session_id)  # the id comes from the client: never let it pick a path like "../x"
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "request": request,
        "model_behavior": behavior,
        "reply": reply,
    }
    with open(LOG_DIR / f"{safe_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
