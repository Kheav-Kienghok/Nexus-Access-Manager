import unittest

from .helpers import NexusCase
from nexusctl import policies as pol


class CliTests(NexusCase):
    def test_project_create_list_delete(self):
        code, out, _ = self.run_cli("project", "create", "speedtest")
        self.assertEqual(code, 0)
        self.assertIn("Created project speedtest", out)
        code, out, _ = self.run_cli("project", "create", "speedtest")
        self.assertIn("already exists", out)
        code, out, _ = self.run_cli("project", "list")
        self.assertIn("speedtest/<image>", out)
        code, _, err = self.run_cli("project", "delete", "speedtest")
        self.assertEqual(code, 2)
        self.assertIn("--yes", err)
        code, out, _ = self.run_cli("project", "delete", "speedtest", "--yes")
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.selectors, {})

    def test_robot_defaults_to_pull_and_push(self):
        self.run_cli("project", "create", "speedtest")
        code, out, _ = self.run_cli("robot", "create", "--project", "speedtest")
        self.assertEqual(code, 0)
        self.assertIn("robot-speedtest", out)
        self.assertIn("pull, push", out)
        self.assertIn("docker login 127.0.0.1:5002 -u robot-speedtest", out)
        self.assertIn("docker pull 127.0.0.1:5000/speedtest/<image>:<tag>", out)
        self.assertIn("pip install --index-url http://robot-speedtest:<password>@127.0.0.1", out)
        password = [l for l in out.splitlines() if l.strip().startswith("password")][0].split()[1]
        self.assertEqual(self.fake.passwords["robot-speedtest"], password)
        self.assertEqual(self.fake.users["robot-speedtest"]["roles"], ["proj-speedtest-pull", "proj-speedtest-push", pol.PIP_ROLE])

    def test_robot_custom_name_and_policy(self):
        self.run_cli("project", "create", "speedtest")
        code, out, _ = self.run_cli("robot", "create", "--name", "ci-pull", "--project", "speedtest", "--policy", "pull", "--no-pip")
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.users["ci-pull"]["roles"], ["proj-speedtest-pull"])
        self.assertNotIn("docker push", out)
        self.assertNotIn("pip install", out)

    def test_missing_project_non_interactive(self):
        code, _, err = self.run_cli("robot", "create", "--project", "nope")
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)
        self.assertIn("--create-project", err)
        code, out, _ = self.run_cli("robot", "create", "--project", "nope", "--create-project")
        self.assertEqual(code, 0)
        self.assertIn("Created project nope", out)
        self.assertIn("robot-nope", self.fake.users)

    def test_robot_without_project_non_interactive(self):
        code, _, err = self.run_cli("robot", "create")
        self.assertEqual(code, 2)
        self.assertIn("--project", err)

    def test_user_gets_full_access_by_default(self):
        self.run_cli("project", "create", "speedtest")
        code, out, _ = self.run_cli("user", "create", "alice", "--project", "speedtest")
        self.assertEqual(code, 0)
        self.assertIn("read, pull, push, update, delete", out)
        self.assertEqual(self.fake.users["alice"]["lastName"], "user")

    def test_user_needs_a_username_non_interactive(self):
        self.run_cli("project", "create", "speedtest")
        code, _, err = self.run_cli("user", "create", "--project", "speedtest")
        self.assertEqual(code, 2)
        self.assertIn("username", err)

    def test_policy_option_validation(self):
        self.run_cli("project", "create", "speedtest")
        code, _, err = self.run_cli("user", "create", "bob", "--project", "speedtest", "--policy", "fly")
        self.assertEqual(code, 2)
        self.assertIn("unknown policy", err)
        self.assertNotIn("bob", self.fake.users)

    def test_password_from_stdin(self):
        self.run_cli("project", "create", "speedtest")
        code, _, _ = self.run_cli("user", "create", "bob", "--project", "speedtest", "--password-stdin", stdin="my-own-password\n")
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.passwords["bob"], "my-own-password")

    def test_account_policy_commands(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("user", "create", "bob", "--project", "speedtest", "--policy", "read,pull")
        code, out, _ = self.run_cli("account", "policy", "bob", "--project", "speedtest", "--add", "push")
        self.assertEqual(code, 0)
        self.assertIn("pull, push", out)
        self.run_cli("account", "policy", "bob", "--project", "speedtest", "--remove", "read")
        self.assertEqual(self.fake.users["bob"]["roles"], ["proj-speedtest-pull", "proj-speedtest-push", pol.PIP_ROLE])
        code, out, _ = self.run_cli("account", "policy", "bob", "--project", "speedtest", "--set", "none")
        self.assertIn("no access", out)
        code, _, err = self.run_cli("account", "policy", "bob", "--project", "speedtest")
        self.assertEqual(code, 2)
        self.assertIn("--set", err)

    def test_account_list_show_pip_password_delete(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("robot", "create", "--project", "speedtest")
        code, out, _ = self.run_cli("account", "list")
        self.assertIn("robot-speedtest", out)
        self.assertIn("pull,push", out)
        code, out, _ = self.run_cli("account", "list", "--project", "other")
        self.assertIn("No accounts", out)
        code, out, _ = self.run_cli("account", "show", "robot-speedtest")
        self.assertIn("project   speedtest: pull, push", out)
        self.run_cli("account", "pip", "robot-speedtest", "off")
        self.assertNotIn(pol.PIP_ROLE, self.fake.users["robot-speedtest"]["roles"])
        code, out, _ = self.run_cli("account", "password", "robot-speedtest", "--password-stdin", stdin="another-secret\n")
        self.assertEqual(self.fake.passwords["robot-speedtest"], "another-secret")
        code, _, err = self.run_cli("account", "delete", "robot-speedtest")
        self.assertEqual(code, 2)
        code, out, _ = self.run_cli("account", "delete", "robot-speedtest", "-y")
        self.assertEqual(code, 0)
        self.assertNotIn("robot-speedtest", self.fake.users)

    def test_refuses_unmanaged_account(self):
        code, _, err = self.run_cli("account", "delete", "admin", "-y")
        self.assertEqual(code, 2)
        self.assertIn("not created by nexusctl", err)

    def test_check(self):
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 0)
        self.assertIn("login works as admin", out)
        self.assertIn("Docker Bearer Token Realm active", out)
        self.fake.repositories = [r for r in self.fake.repositories if r["name"] != "docker-hosted"]
        self.fake.realms.remove("DockerToken")
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 1)
        self.assertIn("docker-hosted missing", out)
        self.assertIn("not active", out)

    def test_wrong_admin_password(self):
        self.env["NEXUS_ADMIN_PASSWORD"] = "wrong"
        code, _, err = self.run_cli("project", "list")
        self.assertEqual(code, 1)
        self.assertIn("401", err)

    def test_unreachable_nexus(self):
        self.env["NEXUS_URL"] = "http://127.0.0.1:9"
        code, _, err = self.run_cli("project", "list")
        self.assertEqual(code, 1)
        self.assertIn("cannot reach Nexus", err)

    def test_missing_url_and_password(self):
        self.env["NEXUS_URL"] = ""
        code, _, err = self.run_cli("project", "list")
        self.assertEqual(code, 2)
        self.assertIn("NEXUS_URL", err)
        self.env["NEXUS_URL"] = self.url
        self.env["NEXUS_ADMIN_PASSWORD"] = ""
        code, _, err = self.run_cli("project", "list")
        self.assertEqual(code, 2)
        self.assertIn("NEXUS_ADMIN_PASSWORD", err)

    def test_resolve_connects_to_ip_but_keeps_the_name(self):
        port = self.url.rsplit(":", 1)[1]
        self.env["NEXUS_URL"] = "http://nexus.example.invalid:%s" % port
        self.env["NEXUS_RESOLVE"] = "127.0.0.1"
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 0, out)

    def test_policies_needs_no_connection(self):
        self.env.clear()
        code, out, _ = self.run_cli("policies")
        self.assertEqual(code, 0)
        self.assertIn("delete", out)
        self.assertIn("robot = pull,push", out)

    def test_help_and_no_command(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("--help")
        self.assertEqual(cm.exception.code, 0)
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("usage: nexusctl", out)

    def test_pypi_repo_is_configurable(self):
        self.env["NEXUS_PYPI_REPO"] = "pypi-proxy"
        self.run_cli("project", "create", "speedtest")
        self.run_cli("robot", "create", "--project", "speedtest")
        self.assertEqual(self.fake.roles[pol.PIP_ROLE]["privileges"],
                         ["nx-repository-view-pypi-pypi-proxy-browse", "nx-repository-view-pypi-pypi-proxy-read"])


if __name__ == "__main__":
    unittest.main()
