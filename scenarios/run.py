"""Runs the conversations in cases.py against the running agent and saves each transcript in examples/.

python scenarios/run.py              # every scenario
python scenarios/run.py alice bob    # only these
python scenarios/run.py --list       # show the names
"""
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # scenarios/ -> project root, where main.py is
sys.path.insert(0, str(ROOT))

from main import AGENT_URL, send  # noqa: E402  (needs the project root on the path first)
from scenarios.cases import SCENARIOS  # noqa: E402

EXAMPLES_DIR = ROOT / "examples"


def quote(text):
    # the reply as a markdown blockquote, so lists and line breaks stay readable in the transcript
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


def run(name, scenario):
    session_id = str(uuid.uuid4())  # a fresh session every run, so earlier runs don't leak into this one
    user = scenario.get("user", name)
    transcript = [f"# {scenario['title']}", ""]

    print(f"\n=== {name}: {scenario['title']}")
    for message in scenario["turns"]:
        print(f"\nyou> {message}")
        print("assistant> ", end="", flush=True)
        parts = []
        try:
            for text in send(session_id, message, user):
                print(text, end="", flush=True)
                parts.append(text)
        except Exception as e:
            print(f"\nerror: {e} (is the agent running at {AGENT_URL}?)")
            return
        print()
        transcript += [f"**Cliente:** {message}", "", "**Melody:**", "", quote("".join(parts)), ""]

    EXAMPLES_DIR.mkdir(exist_ok=True)
    path = EXAMPLES_DIR / f"{name}.md"
    path.write_text("\n".join(transcript), encoding="utf-8")
    print(f"\nsaved in {path}")


def main():
    args = sys.argv[1:]
    if args == ["--list"]:
        for name, scenario in SCENARIOS.items():
            print(f"{name:<24} {scenario['title']}")
        return

    unknown = [name for name in args if name not in SCENARIOS]
    if unknown:
        print(f"unknown scenario(s): {', '.join(unknown)}. Use --list to see the names.")
        return

    for name in args or SCENARIOS:
        run(name, SCENARIOS[name])


if __name__ == "__main__":
    main()
