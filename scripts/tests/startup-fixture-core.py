"""Local-only test Core; copied into a disposable venv project, never production."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def main():
    if os.getenv("STARTUP_FIXTURE_MODE") == "exit":
        raise SystemExit(23)
    data = Path(os.environ["ANIME_AGENT_DATA_DIR"])
    data.mkdir(exist_ok=True)
    impostor = os.getenv("STARTUP_FIXTURE_MODE") == "impostor"
    if not impostor:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])
        (data / "fixture-child.pid").write_text(str(child.pid))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health/live" and not impostor:
                self.send_error(404)
                return
            if not impostor:
                time.sleep(2.3)
            body = json.dumps({"status": "ok", "service": "anime-agent-core",
                               "pid": os.getpid(), "roles": {"avatar": 1}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    ThreadingHTTPServer(("127.0.0.1", int(os.environ["AGENT_CORE_PORT"])), Handler).serve_forever()


if __name__ == '__main__':
    main()
