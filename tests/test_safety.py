import os
import tempfile
import unittest

from astra_core.config import AstraConfig
from astra_core.safety.paths import PathSandbox
from astra_core.safety.shell_policy import ShellPolicy


class PathSandboxTests(unittest.TestCase):
    def test_allows_paths_inside_allowed_root(self):
        with tempfile.TemporaryDirectory() as root:
            config = AstraConfig.default(root)
            sandbox = PathSandbox(config)

            resolved = sandbox.resolve(root, "notes/project.md")

            self.assertTrue(str(resolved).startswith(os.path.abspath(root)))

    def test_rejects_traversal_outside_allowed_root(self):
        with tempfile.TemporaryDirectory() as root:
            config = AstraConfig.default(root)
            sandbox = PathSandbox(config)

            with self.assertRaises(ValueError):
                sandbox.resolve(root, "..")

    def test_rejects_blocked_system_directories(self):
        with tempfile.TemporaryDirectory() as root:
            config = AstraConfig.default(root)
            sandbox = PathSandbox(config)

            with self.assertRaises(ValueError):
                sandbox.assert_allowed(r"C:\Windows\System32")


class ShellPolicyTests(unittest.TestCase):
    def test_allows_safe_read_commands(self):
        policy = ShellPolicy(AstraConfig.default(os.getcwd()))

        assessment = policy.assess("git status")

        self.assertEqual("allow", assessment.decision)
        self.assertFalse(assessment.requires_approval)

    def test_requires_approval_for_write_and_network_commands(self):
        policy = ShellPolicy(AstraConfig.default(os.getcwd()))

        write = policy.assess("mkdir generated")
        network = policy.assess("curl https://example.com")

        self.assertEqual("approval_required", write.decision)
        self.assertEqual("approval_required", network.decision)

    def test_blocks_destructive_commands(self):
        policy = ShellPolicy(AstraConfig.default(os.getcwd()))

        delete = policy.assess("rm -rf .")
        reset = policy.assess("git reset --hard")

        self.assertEqual("deny", delete.decision)
        self.assertEqual("deny", reset.decision)


if __name__ == "__main__":
    unittest.main()
