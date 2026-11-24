import unittest

from .helpers import NexusCase  # noqa: F401  (sets sys.path)
from nexusctl import policies as pol
from nexusctl.config import Config
from nexusctl.errors import UsageError


class PolicyTests(unittest.TestCase):
    def test_parse_names_numbers_aliases(self):
        self.assertEqual(pol.parse_policies("pull,push"), ("pull", "push"))
        self.assertEqual(pol.parse_policies("5 2"), ("pull", "delete"))
        self.assertEqual(pol.parse_policies("all"), pol.POLICIES)
        self.assertEqual(pol.parse_policies("full"), pol.POLICIES)
        self.assertEqual(pol.parse_policies("PUSH, pull"), ("pull", "push"))

    def test_parse_rejects_unknown_and_empty(self):
        with self.assertRaises(UsageError):
            pol.parse_policies("pull,fly")
        with self.assertRaises(UsageError):
            pol.parse_policies(" , ")

    def test_presets(self):
        self.assertEqual(pol.PRESETS["robot"], ("pull", "push"))
        self.assertEqual(pol.PRESETS["user"], ("read", "pull", "push", "update", "delete"))

    def test_role_parse_handles_dashes_in_project(self):
        self.assertEqual(pol.parse_role("proj-speed-test-pull"), ("speed-test", "pull"))
        self.assertEqual(pol.parse_role(pol.role_id("my-app", "delete")), ("my-app", "delete"))
        self.assertIsNone(pol.parse_role("nx-admin"))
        self.assertIsNone(pol.parse_role("proj-x-fly"))

    def test_push_covers_add_and_edit_on_hosted(self):
        cfg = Config()
        (body,) = pol.privilege_bodies("speedtest", "push", cfg)
        self.assertEqual(body["repository"], "docker-hosted")
        self.assertEqual(set(body["actions"]), {"BROWSE", "READ", "ADD", "EDIT"})
        self.assertEqual(body["contentSelector"], "proj-speedtest")

    def test_pull_is_read_only_on_the_group(self):
        (body,) = pol.privilege_bodies("speedtest", "pull", Config())
        self.assertEqual(body["repository"], "docker-all")
        self.assertEqual(set(body["actions"]), {"BROWSE", "READ"})

    def test_delete_has_delete_action(self):
        (body,) = pol.privilege_bodies("speedtest", "delete", Config())
        self.assertIn("DELETE", body["actions"])
        self.assertNotIn("ADD", body["actions"])

    def test_selector_expression_is_scoped_to_the_project(self):
        self.assertEqual(pol.selector_expression("speedtest"), 'format == "docker" and path =^ "/v2/speedtest/"')

    def test_pip_role_uses_configured_repo(self):
        body = pol.pip_role_body(Config(pypi_repo="pypi-proxy"))
        self.assertEqual(body["privileges"], ["nx-repository-view-pypi-pypi-proxy-browse", "nx-repository-view-pypi-pypi-proxy-read"])


if __name__ == "__main__":
    unittest.main()
