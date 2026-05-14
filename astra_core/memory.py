import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime


def _now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class MemoryEntry:
    id: int
    kind: str
    project: str
    title: str
    body: str
    tags: list
    created_at: str
    updated_at: str


class MemoryStore:
    def __init__(self, path, backend="auto"):
        self.path = path
        self.json_path = os.path.join(os.path.dirname(path), "memory.json")
        self.backend = backend
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if backend == "json":
            self._init_json()
        else:
            try:
                self._init()
                self.backend = "sqlite"
            except sqlite3.OperationalError:
                self.backend = "json"
                self._init_json()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    project TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def add(self, project, text, title="", tags=None, kind="note"):
        if self.backend == "json":
            return self._json_add(project, text, title=title, tags=tags, kind=kind)
        tags = tags or []
        timestamp = _now()
        title = title or text[:60]
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memories (kind, project, title, body, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (kind, project, title, text, ", ".join(tags), timestamp, timestamp),
            )
            entry_id = cursor.lastrowid
        return self.get(entry_id)

    def get(self, entry_id):
        if self.backend == "json":
            for entry in self._json_entries():
                if entry.id == entry_id:
                    return entry
            raise KeyError("Memory entry not found: {0}".format(entry_id))
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise KeyError("Memory entry not found: {0}".format(entry_id))
        return self._row_to_entry(row)

    def list_entries(self):
        if self.backend == "json":
            return sorted(self._json_entries(), key=lambda entry: (entry.updated_at, entry.id), reverse=True)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM memories ORDER BY updated_at DESC, id DESC").fetchall()
        return [self._row_to_entry(row) for row in rows]

    def search(self, query):
        if self.backend == "json":
            lowered = query.lower()
            return [
                entry
                for entry in self.list_entries()
                if lowered in entry.title.lower()
                or lowered in entry.body.lower()
                or lowered in entry.project.lower()
                or lowered in ", ".join(entry.tags).lower()
            ]
        pattern = "%{0}%".format(query)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE title LIKE ? OR body LIKE ? OR tags LIKE ? OR project LIKE ?
                ORDER BY updated_at DESC, id DESC
                """,
                (pattern, pattern, pattern, pattern),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def export_markdown(self):
        lines = ["# Astra Memory", ""]
        for entry in self.list_entries():
            lines.append("## {0}".format(entry.title))
            lines.append("")
            lines.append("- id: {0}".format(entry.id))
            lines.append("- kind: {0}".format(entry.kind))
            lines.append("- project: {0}".format(entry.project))
            lines.append("- tags: {0}".format(", ".join(entry.tags)))
            lines.append("- updated: {0}".format(entry.updated_at))
            lines.append("")
            lines.append(entry.body)
            lines.append("")
        return "\n".join(lines)

    def _row_to_entry(self, row):
        tags = [tag.strip() for tag in row[5].split(",") if tag.strip()]
        return MemoryEntry(
            id=row[0],
            kind=row[1],
            project=row[2],
            title=row[3],
            body=row[4],
            tags=tags,
            created_at=row[6],
            updated_at=row[7],
        )

    def _init_json(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, "w", encoding="utf-8") as handle:
                json.dump([], handle)

    def _json_entries(self):
        self._init_json()
        with open(self.json_path, "r", encoding="utf-8") as handle:
            raw_entries = json.load(handle)
        return [
            MemoryEntry(
                id=item["id"],
                kind=item["kind"],
                project=item["project"],
                title=item["title"],
                body=item["body"],
                tags=item.get("tags", []),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )
            for item in raw_entries
        ]

    def _json_add(self, project, text, title="", tags=None, kind="note"):
        tags = tags or []
        entries = self._json_entries()
        timestamp = _now()
        next_id = max([entry.id for entry in entries] or [0]) + 1
        entry = MemoryEntry(
            id=next_id,
            kind=kind,
            project=project,
            title=title or text[:60],
            body=text,
            tags=tags,
            created_at=timestamp,
            updated_at=timestamp,
        )
        entries.append(entry)
        with open(self.json_path, "w", encoding="utf-8") as handle:
            json.dump([asdict(item) for item in entries], handle, indent=2, sort_keys=True)
        return entry
