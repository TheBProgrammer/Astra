import os
from dataclasses import dataclass, field
from typing import List

from astra_core import IDENTITY


def _abs(path):
    return os.path.abspath(os.path.expanduser(path))


@dataclass
class CommandPolicy:
    approval_mode: str = "ask_on_writes"
    read_allowlist: List[str] = field(
        default_factory=lambda: [
            "git",
            "dir",
            "ls",
            "pwd",
            "python",
            "where",
            "whoami",
            "type",
            "Get-ChildItem",
            "Get-Content",
        ]
    )
    approval_commands: List[str] = field(
        default_factory=lambda: [
            "mkdir",
            "new-item",
            "copy",
            "move",
            "curl",
            "wget",
            "npm",
            "pip",
            "uv",
            "uvx",
            "playwright",
            "playwright-cli",
            "code",
            "start-process",
            "taskkill",
        ]
    )
    blocked_patterns: List[str] = field(
        default_factory=lambda: [
            r"\brm\s+-[^\n]*r[^\n]*f",
            r"\bremove-item\b[^\n]*-recurse",
            r"\bdel\b[^\n]*/s",
            r"\brmdir\b[^\n]*/s",
            r"\bformat\b",
            r"\bdiskpart\b",
            r"\bmkfs\b",
            r"\bchmod\s+-?r\b",
            r"\bchown\s+-?r\b",
            r"\bgit\s+reset\s+--hard\b",
            r"\bgit\s+push\b[^\n]*--force",
            r"\bshutdown\b",
            r"\breg\s+delete\b",
        ]
    )


@dataclass
class AstraConfig:
    identity: str
    allowed_roots: List[str]
    blocked_roots: List[str]
    command_policy: CommandPolicy = field(default_factory=CommandPolicy)
    data_dir: str = ""
    remote_enabled: bool = False
    remote_bind_host: str = "127.0.0.1"
    ollama_distro: str = "Ubuntu-22.04"
    ollama_model: str = "astra:latest"
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765

    @classmethod
    def default(cls, root=None):
        selected_root = root or os.environ.get("ASTRA_HOME") or r"D:\Astra"
        allowed = [_abs(selected_root)]
        data_dir = os.path.join(allowed[0], ".astra")
        return cls(
            identity=IDENTITY,
            allowed_roots=allowed,
            blocked_roots=[
                _abs(r"C:\Windows"),
                _abs(r"C:\Program Files"),
                _abs(r"C:\Program Files (x86)"),
                _abs(os.path.join(os.path.expanduser("~"), ".ssh")),
                _abs(os.path.join(os.path.expanduser("~"), ".aws")),
                _abs(os.path.join(os.path.expanduser("~"), ".gnupg")),
                _abs(os.path.join(os.path.expanduser("~"), "AppData", "Roaming")),
            ],
            data_dir=data_dir,
        )

    @property
    def audit_path(self):
        return os.path.join(self.data_dir, "audit.jsonl")

    @property
    def memory_path(self):
        return os.path.join(self.data_dir, "memory.db")
