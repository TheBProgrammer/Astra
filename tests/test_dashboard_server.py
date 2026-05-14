import json
import os
import tempfile
import unittest

from astra_core.config import AstraConfig
from astra_core.web.server import AstraHttpHandler, AstraWebApp


class DashboardServerTests(unittest.TestCase):
    def test_status_payload_contains_backend_and_identity(self):
        with tempfile.TemporaryDirectory() as root:
            app = AstraWebApp(AstraConfig.default(root))

            payload = app.status_payload()

            self.assertEqual("Astra, your local AI systems assistant.", payload["identity"])
            self.assertEqual("astra:latest", payload["backend"]["model"])
            self.assertEqual("Ubuntu-22.04", payload["backend"]["distro"])

    def test_chat_rejects_empty_prompt(self):
        with tempfile.TemporaryDirectory() as root:
            app = AstraWebApp(AstraConfig.default(root))

            status, payload = app.chat_payload("")

            self.assertEqual(400, status)
            self.assertIn("error", payload)

    def test_handler_routes_are_defined(self):
        self.assertTrue(hasattr(AstraHttpHandler, "do_GET"))
        self.assertTrue(hasattr(AstraHttpHandler, "do_POST"))


if __name__ == "__main__":
    unittest.main()
