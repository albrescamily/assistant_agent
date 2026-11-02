import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent_loop import chat

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/chat":
            self.send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            stream = chat(body["message"])
            first = next(stream, "")  # wait for the first chunk so model errors still return 502
        except (ValueError, KeyError) as e:
            self.send_json(400, {"error": f"invalid request: {e}"})
            return
        except Exception as e:
            self.send_json(502, {"error": str(e)})
            return

        # No Content-Length: the text is written as it arrives and the connection closes at the end
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.write_text(first)
        try:
            for text in stream:
                self.write_text(text)
        except Exception as e:
            print(f"stream interrupted: {e}")
            self.write_text(f"\n[error: {e}]")

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
