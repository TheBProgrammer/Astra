import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


def _utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class ActionRecord:
    actor: str
    action_type: str
    command: str = ""
    tool: str = ""
    cwd: str = ""
    decision: str = ""
    result_code: Optional[int] = None
    summary: str = ""
    timestamp: str = field(default_factory=_utc_now)
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class AuditLog:
    def __init__(self, path):
        self.path = path

    def append(self, record):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def tail(self, limit=20):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
