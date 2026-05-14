import re
import subprocess


ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SPINNER_PATTERN = re.compile(r"^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*$")


def clean_ollama_output(output):
    without_ansi = ANSI_PATTERN.sub("", output)
    cleaned_lines = []
    for line in without_ansi.splitlines():
        stripped = line.strip()
        if not stripped or SPINNER_PATTERN.match(stripped):
            continue
        if stripped in ["?", "K"]:
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines).strip()


class OllamaBackend:
    def __init__(self, model="astra:latest", distro="Ubuntu-22.04", timeout_seconds=120):
        self.model = model
        self.distro = distro
        self.timeout_seconds = timeout_seconds

    def build_command(self, prompt):
        escaped = prompt.replace("'", "'\"'\"'")
        shell_command = "OLLAMA_NOHISTORY=1 ollama run {0} '{1}'".format(self.model, escaped)
        return ["wsl", "-d", self.distro, "--", "bash", "-lc", shell_command]

    def generate(self, prompt):
        completed = subprocess.run(
            self.build_command(prompt),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=self.timeout_seconds,
        )
        output = clean_ollama_output(completed.stdout)
        error = clean_ollama_output(completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(error or "Ollama backend failed with code {0}".format(completed.returncode))
        return output

    def metadata(self):
        return {
            "provider": "ollama-wsl",
            "model": self.model,
            "distro": self.distro,
            "status": "configured",
        }
