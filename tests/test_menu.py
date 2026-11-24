import unittest

from .helpers import NexusCase
from nexusctl import policies as pol


class MenuTests(NexusCase):
    def test_menu_lists_numbered_items_and_exits(self):
        code, out, _ = self.run_cli("menu", answers=["00"])
        self.assertEqual(code, 0)
        for line in ("01  Create project", "02  Create user account", "03  Create robot account", "04  Change the policy", "00  Exit"):
            self.assertIn(line, out)

    def test_no_command_in_a_terminal_opens_the_menu(self):
        code, out, _ = self.run_cli(answers=["0"])
        self.assertEqual(code, 0)
        self.assertIn("01  Create project", out)

    def test_robot_with_no_project_asks_to_create_one(self):
        answers = ["03", "", "speedtest", "", "", "", "", "", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertEqual(code, 0)
        self.assertIn("No project exists yet.", out)
        self.assertIn("Created project speedtest", out)
        self.assertIn("Created robot account", out)
        self.assertEqual(self.fake.users["robot-speedtest"]["roles"], ["proj-speedtest-pull", "proj-speedtest-push", pol.PIP_ROLE])

    def test_declining_to_create_a_project_cancels(self):
        code, out, _ = self.run_cli("menu", answers=["03", "n", "00"])
        self.assertIn("Cancelled: a project is needed first", out)
        self.assertNotIn("robot-", " ".join(self.fake.users))

    def test_user_account_defaults_to_full_access(self):
        self.run_cli("project", "create", "speedtest")
        answers = ["02", "", "alice", "", "", "", "", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertIn("Created user account", out)
        for policy in pol.POLICIES:
            self.assertIn("proj-speedtest-%s" % policy, self.fake.users["alice"]["roles"])

    def test_user_picks_policies_by_number_and_own_password(self):
        self.run_cli("project", "create", "speedtest")
        answers = ["02", "speedtest", "bob", "2,3", "n", "n", "", "", "00"]
        # prompts: project, username, policies, pip?, generate password? -> n, then password entry is secret_fn
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertEqual(self.fake.users["bob"]["roles"], ["proj-speedtest-pull", "proj-speedtest-push"])
        self.assertEqual(self.fake.passwords["bob"], "pw-from-prompt")

    def test_new_project_from_the_project_list(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("project", "create", "billing")
        answers = ["03", "n", "newproj", "", "", "", "", "", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertIn("Created project newproj", out)
        self.assertIn("robot-newproj", self.fake.users)

    def test_unknown_project_name_offers_to_create(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("project", "create", "billing")
        answers = ["03", "extra", "y", "", "", "", "", "", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertIn("Created project extra", out)
        self.assertIn("robot-extra", self.fake.users)

    def test_change_policy_from_the_menu(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("user", "create", "alice", "--project", "speedtest")
        answers = ["04", "alice", "", "pull,push", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertIn("alice now has on speedtest: pull, push", out)
        self.assertEqual(self.fake.users["alice"]["roles"], ["proj-speedtest-pull", "proj-speedtest-push", pol.PIP_ROLE])

    def test_remove_all_access_with_none(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("user", "create", "alice", "--project", "speedtest")
        code, out, _ = self.run_cli("menu", answers=["04", "1", "", "none", "00"])
        self.assertIn("no access", out)
        self.assertEqual(self.fake.users["alice"]["roles"], [pol.PIP_ROLE])

    def test_list_reset_delete_from_the_menu(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("robot", "create", "--project", "speedtest")
        code, out, _ = self.run_cli("menu", answers=["05", "06", "07", "1", "", "08", "1", "y", "09", "", "y", "00"])
        self.assertIn("speedtest/<image>", out)
        self.assertIn("robot-speedtest", out)
        self.assertIn("New password for robot-speedtest", out)
        self.assertIn("Deleted account robot-speedtest", out)
        self.assertIn("Deleted project speedtest", out)
        self.assertEqual(self.fake.selectors, {})

    def test_errors_do_not_leave_the_menu(self):
        self.run_cli("project", "create", "speedtest")
        self.run_cli("user", "create", "alice", "--project", "speedtest")
        answers = ["02", "speedtest", "alice", "x", "00"]
        code, out, _ = self.run_cli("menu", answers=answers)
        self.assertEqual(code, 0)
        self.assertIn("Error: user alice already exists", out)

    def test_bad_menu_input(self):
        code, out, _ = self.run_cli("menu", answers=["abc", "99", "", "00"])
        self.assertIn("Type a number", out)
        self.assertIn("No item 99", out)

    def test_check_from_the_menu(self):
        code, out, _ = self.run_cli("menu", answers=["10", "00"])
        self.assertIn("login works as admin", out)


if __name__ == "__main__":
    unittest.main()
