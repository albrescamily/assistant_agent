import argparse
import codecs
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")
SESSIONS_FILE = Path(__file__).parent / "sessions.json"

HELP = """Commands:
  /new    start a new session (for --user, replaces that user's saved session)
  /help   show this help
  /exit   quit"""


def load_sessions():
    if not SESSIONS_FILE.exists():
        return {}
    text = SESSIONS_FILE.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {} 


def save_sessions(sessions):
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


def new_session(user):
    session_id = str(uuid.uuid4())
    if user:
        sessions = load_sessions()
        sessions[user] = session_id
        save_sessions(sessions)
    return session_id


def send(session_id, message, user=None):
    request = urllib.request.Request(
        f"{AGENT_URL}/chat",
        data=json.dumps({"session_id": session_id, "message": message, "user_id": user}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            decoder = codecs.getincrementaldecoder("utf-8")()
            while chunk := response.read1(1024):
                yield decoder.decode(chunk)
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.loads(e.read()).get("error", e.reason))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", help="resume an existing session id")
    parser.add_argument("--user", help="simulate a user: resumes their saved session, or creates one")
    args = parser.parse_args()
    user = args.user

    if args.session:
        session_id = args.session
    elif user and user in load_sessions():
        session_id = load_sessions()[user]
    else:
        session_id = new_session(user)

    print(f"Music store assistant ({AGENT_URL}). Type /help to see the commands.")
    print(f"session: {user or 'anonymous'} ({session_id})")

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/help":
            print(HELP)
            continue
        if user_input == "/new":
            session_id = new_session(user)
            print(f"new session: {user or 'anonymous'} ({session_id})")
            continue

        try:
            print("\nassistant> ", end="", flush=True)
            for text in send(session_id, user_input, user):
                print(text, end="", flush=True)
            print()
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
