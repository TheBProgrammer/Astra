import argparse
import json
import os
import sys

from astra_core import __version__
from astra_core.actions.shell import SafeShell
from astra_core.audit import AuditLog
from astra_core.config import AstraConfig
from astra_core.mcp import generate_mcp_config
from astra_core.memory import MemoryStore
from astra_core.safety.shell_policy import ShellPolicy
from astra_core.web.server import serve


def build_parser():
    parser = argparse.ArgumentParser(prog="astra")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="")
    serve_parser.add_argument("--port", type=int, default=0)

    shell = sub.add_parser("shell")
    shell_sub = shell.add_subparsers(dest="shell_command")
    shell_check = shell_sub.add_parser("check")
    shell_check.add_argument("command_text")
    shell_run = shell_sub.add_parser("run")
    shell_run.add_argument("command_text")
    shell_run.add_argument("--approve", action="store_true")
    shell_run.add_argument("--dry-run", action="store_true")

    memory = sub.add_parser("memory")
    memory_sub = memory.add_subparsers(dest="memory_command")
    memory_add = memory_sub.add_parser("add")
    memory_add.add_argument("--project", required=True)
    memory_add.add_argument("--text", required=True)
    memory_add.add_argument("--title", default="")
    memory_add.add_argument("--tag", action="append", default=[])
    memory_sub.add_parser("list")
    memory_export = memory_sub.add_parser("export")
    memory_export.add_argument("--out", default="")

    mcp = sub.add_parser("mcp")
    mcp_sub = mcp.add_subparsers(dest="mcp_command")
    mcp_config = mcp_sub.add_parser("config")
    mcp_config.add_argument("--target", default="claude-code")
    mcp_config.add_argument("--include-browser", action="store_true")

    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_command")
    audit_tail = audit_sub.add_parser("tail")
    audit_tail.add_argument("--limit", type=int, default=20)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    config = AstraConfig.default()
    audit = AuditLog(config.audit_path)

    if args.command == "status":
        print(config.identity)
        print("version: {0}".format(__version__))
        print("allowed_roots: {0}".format(", ".join(config.allowed_roots)))
        print("backend: ollama-wsl {0} on {1}".format(config.ollama_model, config.ollama_distro))
        print("remote: disabled; localhost preparation only")
        return 0

    if args.command == "serve":
        if args.host:
            config.dashboard_host = args.host
        if args.port:
            config.dashboard_port = args.port
        serve(config)
        return 0

    if args.command == "shell":
        if args.shell_command == "check":
            assessment = ShellPolicy(config).assess(args.command_text)
            print(json.dumps(assessment.__dict__, indent=2, sort_keys=True))
            return 0 if assessment.decision != "deny" else 2
        if args.shell_command == "run":
            result = SafeShell(config, audit).run(
                args.command_text,
                cwd=config.allowed_roots[0],
                approve=args.approve,
                dry_run=args.dry_run,
            )
            if result.stdout:
                sys.stdout.write(result.stdout)
            if result.stderr:
                sys.stderr.write(result.stderr)
            if result.return_code is not None:
                return result.return_code
            return 0 if result.assessment.decision != "deny" else 2

    if args.command == "memory":
        store = MemoryStore(config.memory_path)
        if args.memory_command == "add":
            entry = store.add(args.project, args.text, title=args.title, tags=args.tag)
            print(json.dumps(entry.__dict__, indent=2, sort_keys=True))
            return 0
        if args.memory_command == "list":
            for entry in store.list_entries():
                print("#{0} [{1}] {2}: {3}".format(entry.id, entry.project, entry.title, entry.body))
            return 0
        if args.memory_command == "export":
            exported = store.export_markdown()
            if args.out:
                with open(args.out, "w", encoding="utf-8") as handle:
                    handle.write(exported)
            else:
                print(exported)
            return 0

    if args.command == "mcp" and args.mcp_command == "config":
        print(json.dumps(generate_mcp_config(config, args.target, args.include_browser), indent=2))
        return 0

    if args.command == "audit" and args.audit_command == "tail":
        print(json.dumps(audit.tail(args.limit), indent=2, sort_keys=True))
        return 0

    build_parser().print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
