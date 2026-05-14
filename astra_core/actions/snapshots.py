import subprocess
from dataclasses import dataclass

from astra_core.audit import ActionRecord
from astra_core.safety.paths import PathSandbox


@dataclass
class SnapshotResult:
    return_code: int
    stdout: str
    stderr: str


class GitSnapshot:
    def __init__(self, config, audit_log, timeout_seconds=30):
        self.config = config
        self.audit_log = audit_log
        self.timeout_seconds = timeout_seconds
        self.sandbox = PathSandbox(config)

    def create(self, repo_path, message):
        repo_path = self.sandbox.assert_allowed(repo_path)
        add = self._run(["git", "add", "-A"], repo_path)
        if add.return_code != 0:
            self._log(repo_path, "git add failed", add.return_code)
            return add

        commit = self._run(
            [
                "git",
                "-c",
                "user.name=Astra",
                "-c",
                "user.email=astra@local",
                "commit",
                "-m",
                message,
            ],
            repo_path,
        )
        self._log(repo_path, message, commit.return_code)
        return commit

    def _run(self, args, cwd):
        completed = subprocess.run(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=self.timeout_seconds,
        )
        return SnapshotResult(completed.returncode, completed.stdout, completed.stderr)

    def _log(self, repo_path, summary, result_code):
        self.audit_log.append(
            ActionRecord(
                actor="astra",
                action_type="git_snapshot",
                tool="git",
                cwd=repo_path,
                decision="allow_internal_snapshot",
                result_code=result_code,
                summary=summary,
            )
        )
