import os


def generate_mcp_config(config, target="claude-code", include_browser=False):
    root = os.path.abspath(config.allowed_roots[0])
    filesystem = _npx_command("@modelcontextprotocol/server-filesystem", [root])
    servers = {
        "filesystem": filesystem,
        "git": {
            "command": "uvx",
            "args": ["mcp-server-git", "--repository", root],
        },
    }
    if include_browser:
        servers["playwright"] = _npx_command("@playwright/mcp@latest", [])
    return {
        "target": target,
        "policy": {
            "allowedRoots": config.allowed_roots,
            "terminal": "disabled; use Astra safe shell wrapper",
            "remote": "disabled; localhost-only dashboard preparation",
        },
        "mcpServers": servers,
    }


def _npx_command(package, extra_args):
    if os.name == "nt":
        return {"command": "cmd", "args": ["/c", "npx", "-y", package] + extra_args}
    return {"command": "npx", "args": ["-y", package] + extra_args}
