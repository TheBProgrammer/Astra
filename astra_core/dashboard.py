from astra_core import __version__
from astra_core.audit import AuditLog
from astra_core.memory import MemoryStore


try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover - exercised when FastAPI is absent.
    class _Route:
        def __init__(self, path):
            self.path = path

    class FastAPI:
        def __init__(self, title):
            self.title = title
            self.routes = []

        def get(self, path):
            self.routes.append(_Route(path))

            def decorator(func):
                return func

            return decorator


def create_app(config):
    app = FastAPI(title="Astra Safety Core")

    @app.get("/status")
    def status():
        return {
            "name": "Astra",
            "identity": config.identity,
            "version": __version__,
            "remote_enabled": config.remote_enabled,
            "bind_host": config.remote_bind_host,
            "allowed_roots": config.allowed_roots,
        }

    @app.get("/audit")
    def audit():
        return {"records": AuditLog(config.audit_path).tail(50)}

    @app.get("/memory")
    def memory():
        entries = MemoryStore(config.memory_path).list_entries()
        return {"entries": [entry.__dict__ for entry in entries]}

    return app
