import json
import os
import tempfile
import unittest

from astra_core.audit import AuditLog, ActionRecord
from astra_core.config import AstraConfig
from astra_core.mcp import generate_mcp_config
from astra_core.memory import MemoryStore


class AuditLogTests(unittest.TestCase):
    def test_appends_action_records_as_jsonl(self):
        with tempfile.TemporaryDirectory() as root:
            log = AuditLog(os.path.join(root, "audit.jsonl"))
            record = ActionRecord(
                actor="test",
                action_type="shell",
                command="git status",
                cwd=root,
                decision="allow",
                result_code=0,
            )

            saved = log.append(record)

            with open(log.path, "r", encoding="utf-8") as handle:
                raw = json.loads(handle.readline())
            self.assertEqual(saved.log_id, raw["log_id"])
            self.assertEqual("git status", raw["command"])
            self.assertIn("timestamp", raw)


class MemoryStoreTests(unittest.TestCase):
    def test_adds_lists_searches_and_exports_memory(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(os.path.join(root, "memory.db"))

            entry = store.add(
                project="Astra",
                text="Use bounded shell execution for risky commands.",
                title="Safety preference",
                tags=["safety", "shell"],
            )
            listed = store.list_entries()
            found = store.search("bounded shell")
            exported = store.export_markdown()

            self.assertEqual(entry.id, listed[0].id)
            self.assertEqual(entry.id, found[0].id)
            self.assertIn("Safety preference", exported)
            self.assertIn("safety, shell", exported)

    def test_json_backend_preserves_inspectable_memory_when_sqlite_is_unavailable(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(os.path.join(root, "memory.db"), backend="json")

            entry = store.add(project="Astra", text="Fallback memory stays inspectable.")
            listed = store.list_entries()

            self.assertEqual(entry.id, listed[0].id)
            self.assertTrue(os.path.exists(os.path.join(root, "memory.json")))


class McpConfigTests(unittest.TestCase):
    def test_generates_scoped_filesystem_and_git_config(self):
        with tempfile.TemporaryDirectory() as root:
            config = AstraConfig.default(root)

            generated = generate_mcp_config(config, target="claude-code")

            filesystem = generated["mcpServers"]["filesystem"]
            git = generated["mcpServers"]["git"]
            self.assertIn(os.path.abspath(root), filesystem["args"])
            self.assertIn("--repository", git["args"])
            self.assertNotIn("terminal", generated["mcpServers"])
            self.assertNotIn("shell", generated["mcpServers"])


if __name__ == "__main__":
    unittest.main()
