import json

from pydantic import ValidationError

from tools.registry import REGISTRY


def run_tool(name, arguments):
    tool = REGISTRY.get(name)
    if tool is None:
        return json.dumps({"error": f"unknown tool: {name}"})

    # check the model's arguments against the schema before touching the database
    try:
        params = tool.input_model.model_validate_json(arguments or "{}")
    except ValidationError as e:
        errors = e.errors(include_url=False, include_context=False)
        return json.dumps({"error": "invalid arguments", "details": errors}, default=str)

    try:
        result = tool.fn(**params.model_dump())
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(result, default=str, ensure_ascii=False)
