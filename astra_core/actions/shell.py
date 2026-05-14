import subprocess
from dataclasses import dataclass
from typing import Optional

from astra_core.audit import ActionRecord
from astra_core.safety.paths import PathSandbox
from astra_core.safety.shell_policy import ShellPolicy


@dataclass
class ShellResult:
    assessment: object
    stdout: str = ""
    stderr: str = ""
    return_code: Optional[int] = None
    executed: bool = False


class SafeShell:
    def __init__(self, config, audit_log, timeout_seconds=30):
        self.config = config
        self.audit_log = audit_log
        self.timeout_seconds = timeout_seconds
        self.policy = ShellPolicy(config)
        self.sandbox = PathSandbox(config)

    def run(self, command, cwd=None, approve=False, dry_run=False):
        cwd = cwd or self.config.allowed_roots[0]
        self.sandbox.assert_allowed(cwd)
        assessment = self.policy.assess(command)

        if assessment.decision == "deny":
            self._log(command, cwd, assessment.decision, None, "Command denied")
            return ShellResult(assessment=assessment, stderr="Command denied by Astra policy.")

        if assessment.requires_approval and not approve:
            self._log(command, cwd, assessment.decision, None, "Approval required")
            return ShellResult(assessment=assessment, stderr="Approval required by Astra policy.")

        if dry_run:
            self._log(command, cwd, "dry_run", None, "Dry run only")
            return ShellResult(assessment=assessment, executed=False)

        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=self.timeout_seconds,
        )
        self._log(command, cwd, assessment.decision, completed.returncode, "Command executed")
        return ShellResult(
            assessment=assessment,
            stdout=completed.stdout,
            stderr=completed.stderr,
            return_code=completed.returncode,
            executed=True,
        )

    def _log(self, command, cwd, decision, result_code, summary):
        self.audit_log.append(
            ActionRecord(
                actor="astra",
                action_type="shell",
                command=command,
                cwd=cwd,
                decision=decision,
                result_code=result_code,
                summary=summary,
            )
        )
