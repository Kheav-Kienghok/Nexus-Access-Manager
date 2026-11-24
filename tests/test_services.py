import unittest

from .helpers import NexusCase
from nexusctl import policies as pol
from nexusctl.errors import ProjectMissing, UsageError


class ProjectServiceTests(NexusCase):
    def test_create_builds_selector_privileges_and_roles(self):
        ctx = self.ctx()
        created, kept = ctx.projects.create("speedtest")
        self.assertEqual(ctx.projects.names(), ["speedtest"])
        self.assertIn("proj-speedtest", self.fake.selectors)
        for policy in pol.POLICIES:
            self.assertIn("proj-speedtest-%s" % policy, self.fake.roles)
        self.assertEqual(len(self.fake.privileges), 6)
        self.assertEqual(kept, [])

    def test_create_twice_is_idempotent(self):
        ctx = self.ctx()
        ctx.projects.create("speedtest")
        created, kept = ctx.projects.create("speedtest")
        self.assertEqual(created, [])
        self.assertTrue(kept)
        self.assertEqual(len(self.fake.selectors), 1)

    def test_reserved_and_invalid_names(self):
        ctx = self.ctx()
        for bad in ("library", "Speed", "a b", "-x", ""):
            with self.assertRaises(UsageError):
                ctx.projects.create(bad)

    def test_delete_removes_everything_and_detaches_accounts(self):
        ctx = self.ctx()
        ctx.projects.create("speedtest")
        ctx.accounts.create("robot", "robot-speedtest", "speedtest", ("pull", "push"))
        detached = ctx.projects.delete("speedtest")
        self.assertEqual(detached, ["robot-speedtest"])
        self.assertEqual(ctx.projects.names(), [])
        self.assertEqual(self.fake.privileges, {})
        self.assertFalse([r for r in self.fake.roles if r.startswith("proj-speedtest")])
        self.assertEqual(self.fake.users["robot-speedtest"]["roles"], [pol.PIP_ROLE])


class AccountServiceTests(NexusCase):
    def setUp(self):
        super().setUp()
        self.ctx_ = self.ctx()
        self.ctx_.projects.create("speedtest")

    def test_robot_defaults_pull_push_plus_pip(self):
        created = self.ctx_.accounts.create("robot", "robot-speedtest", "speedtest", pol.PRESETS["robot"])
        roles = self.fake.users["robot-speedtest"]["roles"]
        self.assertEqual(roles, ["proj-speedtest-pull", "proj-speedtest-push", pol.PIP_ROLE])
        self.assertEqual(self.fake.users["robot-speedtest"]["lastName"], "robot")
        self.assertGreaterEqual(len(created.password), 30)
        self.assertEqual(self.fake.passwords["robot-speedtest"], created.password)

    def test_user_gets_full_access(self):
        self.ctx_.accounts.create("user", "alice", "speedtest", pol.PRESETS["user"])
        roles = self.fake.users["alice"]["roles"]
        for policy in pol.POLICIES:
            self.assertIn("proj-speedtest-%s" % policy, roles)

    def test_without_pip(self):
        self.ctx_.accounts.create("user", "bob", "speedtest", ("read", "pull"), pip=False)
        self.assertNotIn(pol.PIP_ROLE, self.fake.users["bob"]["roles"])
        self.assertNotIn(pol.PIP_ROLE, self.fake.roles)

    def test_missing_project_raises(self):
        with self.assertRaises(ProjectMissing):
            self.ctx_.accounts.create("robot", "robot-x", "nope", ("pull",))

    def test_duplicate_user_refused(self):
        self.ctx_.accounts.create("user", "alice", "speedtest", ("pull",))
        with self.assertRaises(UsageError):
            self.ctx_.accounts.create("user", "alice", "speedtest", ("pull",))
        with self.assertRaises(UsageError):
            self.ctx_.accounts.create("user", "admin", "speedtest", ("pull",))

    def test_change_policies_set_add_remove(self):
        acc = self.ctx_.accounts
        acc.create("user", "alice", "speedtest", ("pull",))
        self.assertEqual(acc.change_policies("alice", "speedtest", "add", ("push",)), ("pull", "push"))
        self.assertEqual(acc.change_policies("alice", "speedtest", "remove", ("pull",)), ("push",))
        self.assertEqual(acc.change_policies("alice", "speedtest", "set", ("read", "delete")), ("read", "delete"))
        self.assertEqual(acc.change_policies("alice", "speedtest", "set", ()), ())
        self.assertEqual(self.fake.users["alice"]["roles"], [pol.PIP_ROLE])

    def test_policies_on_two_projects_stay_separate(self):
        self.ctx_.projects.create("billing")
        acc = self.ctx_.accounts
        acc.create("user", "alice", "speedtest", ("pull", "push"))
        acc.change_policies("alice", "billing", "set", ("read",))
        self.assertEqual(acc.get("alice").projects, {"billing": ["read"], "speedtest": ["pull", "push"]})
        acc.change_policies("alice", "speedtest", "set", ("pull",))
        self.assertEqual(acc.get("alice").projects, {"billing": ["read"], "speedtest": ["pull"]})

    def test_pip_toggle(self):
        acc = self.ctx_.accounts
        acc.create("user", "alice", "speedtest", ("pull",), pip=False)
        acc.set_pip("alice", True)
        self.assertIn(pol.PIP_ROLE, self.fake.users["alice"]["roles"])
        acc.set_pip("alice", False)
        self.assertNotIn(pol.PIP_ROLE, self.fake.users["alice"]["roles"])

    def test_unmanaged_users_are_protected(self):
        acc = self.ctx_.accounts
        for action in (lambda: acc.delete("admin"), lambda: acc.reset_password("admin"),
                       lambda: acc.change_policies("admin", "speedtest", "set", ("pull",))):
            with self.assertRaises(UsageError):
                action()
        self.assertIn("admin", self.fake.users)
        self.assertEqual([a.id for a in acc.list()], [])

    def test_reset_password_and_delete(self):
        acc = self.ctx_.accounts
        acc.create("robot", "robot-speedtest", "speedtest", ("pull",))
        new = acc.reset_password("robot-speedtest")
        self.assertEqual(self.fake.passwords["robot-speedtest"], new)
        self.assertEqual(acc.reset_password("robot-speedtest", "chosen-password"), "chosen-password")
        acc.delete("robot-speedtest")
        self.assertNotIn("robot-speedtest", self.fake.users)

    def test_list_filters_by_project(self):
        self.ctx_.projects.create("billing")
        acc = self.ctx_.accounts
        acc.create("user", "alice", "speedtest", ("pull",))
        acc.create("robot", "robot-billing", "billing", ("pull",))
        self.assertEqual([a.id for a in acc.list("billing")], ["robot-billing"])
        self.assertEqual([a.id for a in acc.list()], ["robot-billing", "alice"])


if __name__ == "__main__":
    unittest.main()
