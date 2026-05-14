import os
import shutil
import stat
import subprocess
import tempfile
import unittest

from astra_core.actions.snapshots import GitSnapshot
from astra_core.audit import AuditLog
from astra_core.config import AstraConfig


class GitSnapshotTests(unittest.TestCase):
    def test_creates_git_snapshot_commit_inside_allowed_repo(self):
        root = tempfile.mkdtemp()
        try:
            subprocess.check_call(["git", "init"], cwd=root, stdout=subprocess.DEVNULL)
            with open(os.path.join(root, "note.txt"), "w", encoding="utf-8") as handle:
                handle.write("snapshot me")
            audit = AuditLog(os.path.join(root, "audit.jsonl"))

            snapshot = GitSnapshot(AstraConfig.default(root), audit).create(root, "astra snapshot")

            log = subprocess.check_output(
                ["git", "log", "--oneline", "-1"],
                cwd=root,
                universal_newlines=True,
            )
            self.assertEqual(0, snapshot.return_code)
            self.assertIn("astra snapshot", log)
            self.assertEqual("git_snapshot", audit.tail(1)[0]["action_type"])
        finally:
            shutil.rmtree(root, onerror=_make_writable)


def _make_writable(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


if __name__ == "__main__":
    unittest.main()
