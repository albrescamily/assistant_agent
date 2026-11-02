import json
import os
import urllib.error
import urllib.request

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")

HELP = """Commands:
  /help   show this help
  /exit   quit"""


def send(message):
    request = urllib.request.Request(
        f"{AGENT_URL}/chat",
        data=json.dumps({"message": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())["reply"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.loads(e.read()).get("error", e.reason))


def main():
    print(f"Music store assistant ({AGENT_URL}). Type /help to see the commands.")

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

        try:
            reply = send(user_input)
        except Exception as e:
            print(f"error: {e}")
            continue

        print(f"\nassistant> {reply}")


if __name__ == "__main__":
    main()
