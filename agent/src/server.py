import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from phoenix.otel import register

register(project_name="emporio-agent", auto_instrument=True, protocol="http/protobuf")

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agent.agent_loop import chat

PORT = 8000
tracer = trace.get_tracer(__name__)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/chat":
            self.send_json(404, {"error": "not found"})
            return

         # one parent span per request: the LLM and embedding calls made inside it become its children
        with tracer.start_as_current_span("chat", attributes={"openinference.span.kind": "AGENT"}) as span:
            self.handle_chat(span)

    def handle_chat(self, span):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            span.set_attribute("session.id", body["session_id"])  # groups a conversation's turns in Phoenix's Sessions tab
            span.set_attribute("input.value", body["message"])
            stream = chat(body["message"], body["session_id"])
            first = next(stream, "")  # wait for the first chunk so model errors still return 502
        except (ValueError, KeyError) as e:
            self.send_json(400, {"error": f"invalid request: {e}"})
            return
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            self.send_json(502, {"error": str(e)})
            return

        # No Content-Length: the text is written as it arrives and the connection closes at the end
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        reply = [first]
        self.write_text(first)
        try:
            for text in stream:
                reply.append(text)
                self.write_text(text)
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            self.write_text(f"\n[error: {e}]")
        span.set_attribute("output.value", "".join(reply))  # the full answer, shown on the trace row

    def write_text(self, text):
        self.wfile.write(text.encode())
        self.wfile.flush()

    def send_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    print(f"Agent listening on port {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
