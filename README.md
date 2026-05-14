# Astra OS Safety Core v0.1

Astra is a local-first AI operating layer foundation focused on bounded autonomy,
safe shell execution, transparent memory, audit logs, and policy-wrapped tool
adapters.

Identity:

> Astra, your local AI systems assistant.

## Quick Start

```powershell
python -m astra_cli status
python -m astra_cli shell check "git status"
python -m astra_cli shell run "python --version"
python -m astra_cli memory add --project Astra --text "Prefer bounded shell execution."
python -m astra_cli memory list
python -m astra_cli mcp config --target claude-code
python -m astra_cli audit tail
python -m astra_cli serve
```

Default allowed root is the current `ASTRA_HOME` environment variable, falling
back to `D:\Astra` when unset.

## Local Dashboard

Run:

```powershell
python -m astra_cli serve
```

Then open `http://127.0.0.1:8765`.

The dashboard is localhost-only and uses the WSL Ollama backend by default:

- distro: `Ubuntu-22.04`
- model: `astra:latest`
