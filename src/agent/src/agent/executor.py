import json

from pydantic import ValidationError

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import ValidationError

from tools.registry import REGISTRY

tracer = trace.get_tracer(__name__)

def run_tool(name, arguments):
    # one span per tool call, so Phoenix shows which tool ran, with what arguments and what it returned
    with tracer.start_as_current_span(f"tool {name}", attributes={
        "openinference.span.kind": "TOOL",
        "tool.name": name,
        "input.value": arguments or "{}",
    }) as span:
        result = json.dumps(execute(name, arguments, span), default=str, ensure_ascii=False)
        span.set_attribute("output.value", result)
        return result


def execute(name, arguments, span):
    tool = REGISTRY.get(name)
    if tool is None:
        span.set_status(Status(StatusCode.ERROR, "unknown tool"))
        return {"error": f"unknown tool: {name}"}

    # check the model's arguments against the schema before touching the database
    try:
        params = tool.input_model.model_validate_json(arguments or "{}")
    except ValidationError as e:
        span.set_status(Status(StatusCode.ERROR, "invalid arguments"))  # the model sent bad arguments
        return {"error": "invalid arguments", "details": e.errors(include_url=False, include_context=False)}

    try:
        return tool.fn(**params.model_dump())
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR))
        return {"error": str(e)}
