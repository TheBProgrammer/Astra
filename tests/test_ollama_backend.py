import unittest

from astra_core.backends.ollama import OllamaBackend, clean_ollama_output


class OllamaBackendTests(unittest.TestCase):
    def test_builds_wsl_command_for_astra_model(self):
        backend = OllamaBackend(model="astra:latest", distro="Ubuntu-22.04")

        command = backend.build_command("Hello Astra")

        self.assertEqual("wsl", command[0])
        self.assertIn("Ubuntu-22.04", command)
        self.assertIn("ollama run astra:latest", command[-1])

    def test_cleans_ollama_spinner_control_sequences(self):
        raw = "Astra online.\n\x1b[?25l\x1b[1G⠙ \x1b[K\x1b[?25h"

        cleaned = clean_ollama_output(raw)

        self.assertEqual("Astra online.", cleaned)


if __name__ == "__main__":
    unittest.main()
