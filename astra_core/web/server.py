import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from astra_core import __version__
from astra_core.audit import AuditLog
from astra_core.backends.ollama import OllamaBackend
from astra_core.memory import MemoryStore


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Astra OS</title>
  <style>
    :root { color-scheme: dark; font-family: Segoe UI, system-ui, sans-serif; }
    body { margin: 0; background: #0b0f14; color: #e9eef5; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px; }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: start; border-bottom: 1px solid #263241; padding-bottom: 20px; }
    h1 { margin: 0 0 8px; font-size: 32px; letter-spacing: 0; }
    .muted { color: #9fb0c4; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 20px 0; }
    .panel { border: 1px solid #263241; border-radius: 8px; padding: 16px; background: #111821; }
    label { display: block; color: #9fb0c4; margin-bottom: 8px; }
    textarea { width: 100%; min-height: 120px; resize: vertical; box-sizing: border-box; border-radius: 8px; border: 1px solid #344456; background: #090d12; color: #e9eef5; padding: 12px; font: inherit; }
    button { border: 0; border-radius: 8px; padding: 10px 14px; background: #3fc6a2; color: #06110e; font-weight: 700; cursor: pointer; margin-top: 10px; }
    pre { white-space: pre-wrap; word-break: break-word; background: #090d12; border: 1px solid #263241; border-radius: 8px; padding: 14px; min-height: 80px; }
    code { color: #92d6ff; }
  </style>
</head>
<body>
  <main>
    <header>
      <section>
        <h1>Astra OS</h1>
        <div id="identity" class="muted">Loading...</div>
      </section>
      <code id="version"></code>
    </header>
    <section class="grid">
      <div class="panel"><strong>Backend</strong><div id="backend" class="muted"></div></div>
      <div class="panel"><strong>Sandbox</strong><div id="roots" class="muted"></div></div>
      <div class="panel"><strong>Remote</strong><div class="muted">Disabled. Localhost only.</div></div>
    </section>
    <section class="panel">
      <label for="prompt">Chat with Astra</label>
      <textarea id="prompt">Identify yourself and summarize your current safety mode.</textarea>
      <button id="send">Send</button>
      <pre id="response">Ready.</pre>
    </section>
  </main>
  <script>
    async function loadStatus() {
      const status = await fetch('/api/status').then(r => r.json());
      document.getElementById('identity').textContent = status.identity;
      document.getElementById('version').textContent = 'v' + status.version;
      document.getElementById('backend').textContent = status.backend.provider + ' / ' + status.backend.model + ' / ' + status.backend.distro;
      document.getElementById('roots').textContent = status.allowed_roots.join(', ');
    }
    document.getElementById('send').addEventListener('click', async () => {
      const output = document.getElementById('response');
      output.textContent = 'Thinking...';
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt: document.getElementById('prompt').value})
      });
      const payload = await response.json();
      output.textContent = payload.response || payload.error || 'No response.';
    });
    loadStatus().catch(err => document.getElementById('identity').textContent = err.message);
  </script>
</body>
</html>
"""


class AstraWebApp:
    def __init__(self, config):
        self.config = config
        self.backend = OllamaBackend(
            model=config.ollama_model,
            distro=config.ollama_distro,
            api_url=config.ollama_api_url,
        )

    def status_payload(self):
        return {
            "name": "Astra",
            "identity": self.config.identity,
            "version": __version__,
            "allowed_roots": self.config.allowed_roots,
            "remote_enabled": self.config.remote_enabled,
            "backend": self.backend.metadata(),
        }

    def chat_payload(self, prompt):
        prompt = (prompt or "").strip()
        if not prompt:
            return 400, {"error": "Prompt is required."}
        response = self.backend.generate(prompt)
        return 200, {"response": response}

    def audit_payload(self):
        return {"records": AuditLog(self.config.audit_path).tail(50)}

    def memory_payload(self):
        entries = MemoryStore(self.config.memory_path).list_entries()
        return {"entries": [entry.__dict__ for entry in entries]}


class AstraHttpHandler(BaseHTTPRequestHandler):
    app = None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/api/status":
            self._send_json(200, self.app.status_payload())
        elif path == "/api/audit":
            self._send_json(200, self.app.audit_payload())
        elif path == "/api/memory":
            self._send_json(200, self.app.memory_payload())
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body)
            status, response = self.app.chat_payload(payload.get("prompt", ""))
        except Exception as exc:
            status, response = 500, {"error": str(exc)}
        self._send_json(status, response)

    def log_message(self, fmt, *args):
        return

    def _send_html(self, html):
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status, payload):
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve(config):
    AstraHttpHandler.app = AstraWebApp(config)
    server = ThreadingHTTPServer((config.dashboard_host, config.dashboard_port), AstraHttpHandler)
    print("Astra dashboard: http://{0}:{1}".format(config.dashboard_host, config.dashboard_port), flush=True)
    server.serve_forever()
