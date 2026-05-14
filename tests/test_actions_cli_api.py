import json
import os
import subprocess
import sys
import tempfile
import unittest

from astra_core.actions.shell import SafeShell
from astra_core.audit import AuditLog
from astra_core.config import AstraConfig
from astra_core.dashboard import create_app


class SafeShellTests(unittest.TestCase):
    def test_logs_allowed_command_results(self):
        with tempfile.TemporaryDirectory() as root:
            audit = AuditLog(os.path.join(root, "audit.jsonl"))
            shell = SafeShell(AstraConfig.default(root), audit)

            result = shell.run("python --version", cwd=root)

            self.assertEqual("allow", result.assessment.decision)
            self.assertEqual(0, result.return_code)
            self.assertIn("Python", result.stdout + result.stderr)
            with open(audit.path, "r", encoding="utf-8") as handle:
                self.assertEqual("shell", json.loads(handle.readline())["action_type"])

    def test_does_not_execute_approval_required_command_without_approval(self):
        with tempfile.TemporaryDirectory() as root:
            audit = AuditLog(os.path.join(root, "audit.jsonl"))
            shell = SafeShell(AstraConfig.default(root), audit)

            result = shell.run("mkdir generated", cwd=root)

            self.assertEqual("approval_required", result.assessment.decision)
            self.assertIsNone(result.return_code)
            self.assertFalse(os.path.exists(os.path.join(root, "generated")))


class CliTests(unittest.TestCase):
    def test_status_cli_identifies_as_astra(self):
        env = os.environ.copy()
        env["ASTRA_HOME"] = tempfile.mkdtemp()
        completed = subprocess.run(
            [sys.executable, "-m", "astra_cli", "status"],
            cwd=os.getcwd(),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        self.assertEqual(0, completed.returncode)
        self.assertIn("Astra, your local AI systems assistant.", completed.stdout)


class DashboardTests(unittest.TestCase):
    def test_create_app_exposes_local_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            app = create_app(AstraConfig.default(root))

            self.assertEqual("Astra Safety Core", app.title)
            routes = [route.path for route in app.routes]
            self.assertIn("/status", routes)
            self.assertIn("/audit", routes)
            self.assertIn("/memory", routes)


if __name__ == "__main__":
    unittest.main()
