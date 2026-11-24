from __future__ import annotations

from dataclasses import dataclass, field

from .client import user_update_body
from .errors import ProjectMissing, UsageError
from .policies import (
    MANAGED_MARK,
    PIP_ROLE,
    normalise,
    parse_role,
    pip_role_body,
    role_id,
)
from .util import generate_password, validate_username


@dataclass
class Account:
    id: str
    kind: str
    status: str
    email: str
    roles: list = field(default_factory=list)

    @property
    def projects(self):
        found = {}
        for role in self.roles:
            parsed = parse_role(role)
            if parsed:
                found.setdefault(parsed[0], []).append(parsed[1])
        return {name: list(normalise(items)) for name, items in sorted(found.items())}

    @property
    def pip(self):
        return PIP_ROLE in self.roles


@dataclass
class Created:
    username: str
    password: str
    kind: str
    project: str
    policies: tuple
    pip: bool


class AccountService:
    def __init__(self, client, cfg, projects):
        self.client = client
        self.cfg = cfg
        self.projects = projects

    @staticmethod
    def _managed(raw):
        return raw.get("firstName") == MANAGED_MARK

    @staticmethod
    def _account(raw):
        return Account(
            id=raw["userId"],
            kind=raw.get("lastName") or "user",
            status=raw.get("status", ""),
            email=raw.get("emailAddress", ""),
            roles=list(raw.get("roles") or []),
        )

    def _find(self, username):
        for raw in self.client.users():
            if raw.get("userId") == username:
                return raw
        return None

    def managed_raw(self, username):
        raw = self._find(username)
        if raw is None:
            raise UsageError("no such account: %s" % username)
        if not self._managed(raw):
            raise UsageError("%s was not created by nexusctl, refusing to change it" % username)
        return raw

    def list(self, project=None):
        accounts = [self._account(r) for r in self.client.users() if self._managed(r)]
        if project:
            accounts = [a for a in accounts if project in a.projects]
        return sorted(accounts, key=lambda a: (a.kind, a.id))

    def get(self, username):
        return self._account(self.managed_raw(username))

    def ensure_pip_role(self):
        body = pip_role_body(self.cfg)
        if PIP_ROLE in {r["id"] for r in self.client.roles()}:
            self.client.update_role(PIP_ROLE, body)
        else:
            self.client.create_role(body)

    def create(self, kind, username, project, policies, pip=True, password=None, email=None):
        validate_username(username)
        if self._find(username) is not None:
            raise UsageError("user %s already exists" % username)
        if not self.projects.exists(project):
            raise ProjectMissing(project)
        policies = normalise(policies)
        if not policies:
            raise UsageError("give at least one policy")

        roles = [role_id(project, p) for p in policies]
        if pip:
            self.ensure_pip_role()
            roles.append(PIP_ROLE)

        password = password or generate_password(kind)
        self.client.create_user(
            {
                "userId": username,
                "firstName": MANAGED_MARK,
                "lastName": kind,
                "emailAddress": email or "%s@%s" % (username, self.cfg.email_domain),
                "password": password,
                "status": "active",
                "roles": roles,
            }
        )
        return Created(username, password, kind, project, policies, pip)

    def set_policies(self, username, project, policies):
        raw = self.managed_raw(username)
        policies = normalise(policies)
        if policies and not self.projects.exists(project):
            raise ProjectMissing(project)
        held = {}
        others = []
        for role in raw.get("roles") or []:
            parsed = parse_role(role)
            if parsed is None:
                others.append(role)
            elif parsed[0] != project:
                held.setdefault(parsed[0], set()).add(parsed[1])
        if policies:
            held[project] = set(policies)
        roles = [role_id(name, p) for name in sorted(held) for p in normalise(held[name])]
        self.client.update_user(username, user_update_body(raw, roles + others))
        return policies

    def change_policies(self, username, project, mode, policies):
        current = set(self.get(username).projects.get(project, []))
        wanted = set(normalise(policies))
        if mode == "set":
            new = wanted
        elif mode == "add":
            new = current | wanted
        elif mode == "remove":
            new = current - wanted
        else:
            raise UsageError("mode must be set, add or remove")
        return self.set_policies(username, project, new)

    def set_pip(self, username, enabled):
        raw = self.managed_raw(username)
        roles = [r for r in raw.get("roles") or [] if r != PIP_ROLE]
        if enabled:
            self.ensure_pip_role()
            roles.append(PIP_ROLE)
        self.client.update_user(username, user_update_body(raw, roles))

    def reset_password(self, username, password=None):
        raw = self.managed_raw(username)
        password = password or generate_password(raw.get("lastName") or "user")
        self.client.change_password(username, password)
        return password

    def delete(self, username):
        self.managed_raw(username)
        self.client.delete_user(username)
