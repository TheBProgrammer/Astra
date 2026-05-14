import os


class PathSandbox:
    def __init__(self, config):
        self.config = config

    def resolve(self, base, candidate):
        base_path = os.path.abspath(base)
        if os.path.isabs(candidate):
            resolved = os.path.abspath(candidate)
        else:
            resolved = os.path.abspath(os.path.join(base_path, candidate))
        self.assert_allowed(resolved)
        return resolved

    def assert_allowed(self, path):
        resolved = os.path.abspath(path)
        lowered = resolved.lower()

        for blocked in self.config.blocked_roots:
            blocked_abs = os.path.abspath(blocked).lower()
            if lowered == blocked_abs or lowered.startswith(blocked_abs + os.sep.lower()):
                raise ValueError("Path is blocked by Astra policy: {0}".format(resolved))

        for root in self.config.allowed_roots:
            root_abs = os.path.abspath(root).lower()
            if lowered == root_abs or lowered.startswith(root_abs + os.sep.lower()):
                return resolved

        raise ValueError("Path is outside Astra allowed roots: {0}".format(resolved))
