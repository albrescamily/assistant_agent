import json

from tools.tools import FUNCTIONS


def run_tool(name, arguments):
    function = FUNCTIONS.get(name)
    if function is None:
        return json.dumps({"error": f"unknown tool: {name}"})

    try:
        args = json.loads(arguments or "{}")
        result = function(**args)
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(result, default=str, ensure_ascii=False)
