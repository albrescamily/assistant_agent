import argparse
import codecs
import json
import os
import urllib.error
import urllib.request
import uuid

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")

HELP = """Commands:
  /new    start a new session
  /help   show this help
  /exit   quit"""


def send(session_id, message):
    request = urllib.request.Request(
        f"{AGENT_URL}/chat",
        data=json.dumps({"session_id": session_id, "message": message}).encode(),
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
    session_id = parser.parse_args().session or str(uuid.uuid4())

    print(f"Music store assistant ({AGENT_URL}). Type /help to see the commands.")
    print(f"session: {session_id}")

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
            session_id = str(uuid.uuid4())
            print(f"new session: {session_id}")
            continue

        try:
            print("\nassistant> ", end="", flush=True)
            for text in send(session_id, user_input):
                print(text, end="", flush=True)
            print()
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
