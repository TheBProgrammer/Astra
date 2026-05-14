import json
import re
import subprocess
import time
import urllib.request


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
    def __init__(self, model="astra:latest", distro="Ubuntu-22.04", timeout_seconds=120, api_url="http://127.0.0.1:11434"):
        self.model = model
        self.distro = distro
        self.timeout_seconds = timeout_seconds
        self.api_url = api_url.rstrip("/") if api_url else ""

    def build_command(self, prompt):
        shell_command = "OLLAMA_NOHISTORY=1 ollama run {0}".format(self.model)
        return ["wsl", "-d", self.distro, "--", "bash", "-lc", shell_command]

    def generate(self, prompt):
        if self.api_url:
            try:
                return self._generate_http(prompt)
            except Exception:
                self._start_ollama_server()
                try:
                    return self._generate_http(prompt)
                except Exception:
                    try:
                        return self._generate_wsl_http(prompt)
                    except Exception:
                        pass
        completed = subprocess.run(
            self.build_command(prompt),
            input=prompt + "\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )
        output = clean_ollama_output(completed.stdout)
        error = clean_ollama_output(completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(error or "Ollama backend failed with code {0}".format(completed.returncode))
        return output

    def _generate_http(self, prompt):
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.api_url + "/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        raw = urllib.request.urlopen(request, timeout=self.timeout_seconds).read().decode("utf-8")
        response = json.loads(raw)
        if "error" in response:
            raise RuntimeError(response["error"])
        return response.get("response", "").strip()

    def _start_ollama_server(self):
        subprocess.Popen(
            [
                "wsl",
                "-d",
                self.distro,
                "--",
                "bash",
                "-lc",
                "nohup ollama serve >/tmp/astra-ollama.log 2>&1 &",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urllib.request.urlopen(self.api_url + "/api/tags", timeout=2).read()
                return
            except Exception:
                time.sleep(0.5)

    def _generate_wsl_http(self, prompt):
        script = (
            "import json, sys, urllib.request\n"
            "payload=json.loads(sys.stdin.read())\n"
            "data=json.dumps(payload).encode('utf-8')\n"
            "req=urllib.request.Request('http://127.0.0.1:11434/api/generate', "
            "data=data, headers={{'Content-Type':'application/json'}})\n"
            "print(urllib.request.urlopen(req, timeout={0}).read().decode('utf-8'))\n"
        ).format(int(self.timeout_seconds))
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False})
        completed = subprocess.run(
            ["wsl", "-d", self.distro, "--", "python3", "-c", script],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(clean_ollama_output(completed.stderr) or "WSL Ollama API failed")
        response = json.loads(completed.stdout)
        if "error" in response:
            raise RuntimeError(response["error"])
        return response.get("response", "").strip()

    def metadata(self):
        return {
            "provider": "ollama-wsl",
            "model": self.model,
            "distro": self.distro,
            "api_url": self.api_url,
            "status": "configured",
        }
