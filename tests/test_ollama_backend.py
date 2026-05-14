import unittest
from unittest.mock import patch

from astra_core.backends.ollama import OllamaBackend, clean_ollama_output


class OllamaBackendTests(unittest.TestCase):
    def test_builds_wsl_command_for_astra_model(self):
        backend = OllamaBackend(model="astra:latest", distro="Ubuntu-22.04")

        command = backend.build_command("Hello Astra")

        self.assertEqual("wsl", command[0])
        self.assertIn("Ubuntu-22.04", command)
        self.assertIn("ollama run astra:latest", command[-1])
        self.assertNotIn("Hello Astra", command[-1])

    def test_cleans_ollama_spinner_control_sequences(self):
        raw = "Astra online.\n\x1b[?25l\x1b[1G⠙ \x1b[K\x1b[?25h"

        cleaned = clean_ollama_output(raw)

        self.assertEqual("Astra online.", cleaned)

    def test_generate_decodes_wsl_output_as_utf8_with_replacement(self):
        backend = OllamaBackend(api_url="")

        with patch("astra_core.backends.ollama.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "Astra online."
            run.return_value.stderr = ""

            self.assertEqual("Astra online.", backend.generate("hello"))

        self.assertEqual("utf-8", run.call_args[1]["encoding"])
        self.assertEqual("replace", run.call_args[1]["errors"])
        self.assertEqual("hello\n", run.call_args[1]["input"])

    def test_generate_prefers_clean_ollama_http_api(self):
        backend = OllamaBackend(api_url="http://127.0.0.1:11434")

        class Response:
            def read(self):
                return b'{"response":"Astra online.","done":true}'

        with patch("astra_core.backends.ollama.urllib.request.urlopen", return_value=Response()) as urlopen:
            response = backend.generate("hello")

        self.assertEqual("Astra online.", response)
        request = urlopen.call_args[0][0]
        self.assertEqual("http://127.0.0.1:11434/api/generate", request.full_url)

    def test_generate_starts_wsl_ollama_when_http_api_is_down(self):
        backend = OllamaBackend(api_url="http://127.0.0.1:11434")

        with patch("astra_core.backends.ollama.urllib.request.urlopen") as urlopen:
            urlopen.side_effect = OSError("down")
            with patch.object(backend, "_start_ollama_server") as start:
                with patch.object(backend, "_generate_wsl_http", return_value="Astra online.") as wsl_http:
                    response = backend.generate("hello")

        self.assertEqual("Astra online.", response)
        self.assertEqual(1, start.call_count)
        self.assertEqual(1, wsl_http.call_count)

    def test_wsl_http_generation_parses_clean_json_response(self):
        backend = OllamaBackend(api_url="")

        with patch("astra_core.backends.ollama.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"response":"Astra online."}'
            run.return_value.stderr = ""

            response = backend._generate_wsl_http("hello")

        self.assertEqual("Astra online.", response)
        self.assertIn("python3", run.call_args[0][0])
        self.assertEqual("utf-8", run.call_args[1]["encoding"])
        self.assertEqual("replace", run.call_args[1]["errors"])
        self.assertIn('"prompt": "hello"', run.call_args[1]["input"])


if __name__ == "__main__":
    unittest.main()
