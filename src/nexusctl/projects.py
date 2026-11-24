from __future__ import annotations

from . import policies as pol
from .client import user_update_body
from .util import validate_project


class ProjectService:
    def __init__(self, client, cfg):
        self.client = client
        self.cfg = cfg

    def names(self):
        found = []
        for sel in self.client.selectors():
            name = sel.get("name", "")
            described = (sel.get("description") or "").startswith(pol.DESCRIPTION_PREFIX)
            if name.startswith(pol.PROJECT_PREFIX) and described:
                found.append(name[len(pol.PROJECT_PREFIX):])
        return sorted(found)

    def exists(self, name):
        return name in self.names()

    def create(self, name):
        validate_project(name)
        created, kept = [], []

        selector = pol.selector_body(name)
        if selector["name"] in {s["name"] for s in self.client.selectors()}:
            kept.append("selector " + selector["name"])
        else:
            self.client.create_selector(selector)
            created.append("selector " + selector["name"])

        known = {p["name"] for p in self.client.privileges()}
        for policy in pol.POLICIES:
            for body in pol.privilege_bodies(name, policy, self.cfg):
                if body["name"] in known:
                    kept.append("privilege " + body["name"])
                else:
                    self.client.create_privilege(body)
                    created.append("privilege " + body["name"])

        roles = {r["id"] for r in self.client.roles()}
        for policy in pol.POLICIES:
            body = pol.role_body(name, policy, self.cfg)
            if body["id"] in roles:
                self.client.update_role(body["id"], body)
                kept.append("role " + body["id"])
            else:
                self.client.create_role(body)
                created.append("role " + body["id"])
        return created, kept

    def delete(self, name):
        role_ids = [pol.role_id(name, p) for p in pol.POLICIES]
        detached = []
        for user in self.client.users():
            roles = user.get("roles") or []
            remaining = [r for r in roles if r not in role_ids]
            if remaining != roles:
                self.client.update_user(user["userId"], user_update_body(user, remaining))
                detached.append(user["userId"])

        existing_roles = {r["id"] for r in self.client.roles()}
        for rid in role_ids:
            if rid in existing_roles:
                self.client.delete_role(rid)

        existing_privileges = {p["name"] for p in self.client.privileges()}
        for policy in pol.POLICIES:
            for body in pol.privilege_bodies(name, policy, self.cfg):
                if body["name"] in existing_privileges:
                    self.client.delete_privilege(body["name"])

        if pol.selector_name(name) in {s["name"] for s in self.client.selectors()}:
            self.client.delete_selector(pol.selector_name(name))
        return detached
