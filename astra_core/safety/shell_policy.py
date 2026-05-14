import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class CommandAssessment:
    command: str
    risk_level: str
    requires_approval: bool
    matched_rules: List[str] = field(default_factory=list)
    decision: str = "deny"


class ShellPolicy:
    def __init__(self, config):
        self.config = config

    def assess(self, command):
        normalized = command.strip()
        lowered = normalized.lower()
        matches = []

        if not normalized:
            return CommandAssessment(command, "blocked", False, ["empty command"], "deny")

        for pattern in self.config.command_policy.blocked_patterns:
            if re.search(pattern, lowered, re.IGNORECASE):
                matches.append(pattern)
        if self._has_obfuscation(lowered):
            matches.append("shell obfuscation or command chaining")
        if matches:
            return CommandAssessment(command, "blocked", False, matches, "deny")

        first = self._first_token(lowered)
        for approval_command in self.config.command_policy.approval_commands:
            if first == approval_command.lower():
                return CommandAssessment(
                    command,
                    "write_or_external",
                    True,
                    ["approval command: {0}".format(approval_command)],
                    "approval_required",
                )

        if first in [item.lower() for item in self.config.command_policy.read_allowlist]:
            if first == "git" and self._git_subcommand_requires_approval(lowered):
                return CommandAssessment(
                    command,
                    "write_or_external",
                    True,
                    ["git write operation"],
                    "approval_required",
                )
            return CommandAssessment(command, "read", False, ["read allowlist: {0}".format(first)], "allow")

        return CommandAssessment(command, "unknown", True, ["unknown command"], "approval_required")

    def _first_token(self, command):
        return command.split()[0] if command.split() else ""

    def _has_obfuscation(self, command):
        suspicious = ["&&", "||", ";", "$(", "`", ">", "<"]
        return any(token in command for token in suspicious)

    def _git_subcommand_requires_approval(self, command):
        write_subcommands = [
            " add",
            " commit",
            " checkout",
            " switch",
            " merge",
            " rebase",
            " pull",
            " push",
            " clean",
            " init",
            " branch -d",
            " branch -D",
        ]
        return any(token.lower() in command for token in write_subcommands)
