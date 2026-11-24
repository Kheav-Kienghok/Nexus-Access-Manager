from __future__ import annotations

from .errors import UsageError

PROJECT_PREFIX = "proj-"
DESCRIPTION_PREFIX = "nexusctl project "
PIP_ROLE = "nexusctl-pip-pull"
MANAGED_MARK = "nexusctl"

POLICIES = ("read", "pull", "push", "update", "delete")

SUMMARY = {
    "read": "view images in the Nexus UI and search",
    "pull": "docker pull",
    "push": "docker push (new tags, and overwriting a tag such as latest)",
    "update": "modify or overwrite existing tags in the UI or API",
    "delete": "delete tags and layers",
}

PRESETS = {
    "robot": ("pull", "push"),
    "user": POLICIES,
}

ALIASES = {
    "all": POLICIES,
    "full": POLICIES,
    "view": ("read",),
    "write": ("push", "update"),
}

_SUFFIX = {"pull_repo": "all", "push_repo": "hosted"}

_SPEC = {
    "read": (("pull_repo", ("BROWSE",)), ("push_repo", ("BROWSE",))),
    "pull": (("pull_repo", ("BROWSE", "READ")),),
    "push": (("push_repo", ("BROWSE", "READ", "ADD", "EDIT")),),
    "update": (("push_repo", ("BROWSE", "READ", "EDIT")),),
    "delete": (("push_repo", ("BROWSE", "READ", "DELETE")),),
}


def normalise(policies):
    wanted = set(policies)
    return tuple(p for p in POLICIES if p in wanted)


def parse_policies(text):
    wanted = []
    for token in str(text).replace(" ", ",").split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token.isdigit() and 1 <= int(token) <= len(POLICIES):
            wanted.append(POLICIES[int(token) - 1])
        elif token in POLICIES:
            wanted.append(token)
        elif token in ALIASES:
            wanted.extend(ALIASES[token])
        else:
            raise UsageError(
                "unknown policy %r, choose from: %s, or all" % (token, ", ".join(POLICIES))
            )
    if not wanted:
        raise UsageError("give at least one policy: %s" % ", ".join(POLICIES))
    return normalise(wanted)


def selector_name(project):
    return PROJECT_PREFIX + project


def selector_expression(project):
    return 'format == "docker" and path =^ "/v2/%s/"' % project


def selector_body(project):
    return {
        "name": selector_name(project),
        "description": DESCRIPTION_PREFIX + project,
        "expression": selector_expression(project),
    }


def privilege_name(project, policy, key):
    return "%s%s-%s-%s" % (PROJECT_PREFIX, project, policy, _SUFFIX[key])


def privilege_bodies(project, policy, cfg):
    bodies = []
    for key, actions in _SPEC[policy]:
        repo = getattr(cfg, key)
        bodies.append(
            {
                "name": privilege_name(project, policy, key),
                "description": "%s on project %s (%s)" % (policy, project, repo),
                "actions": list(actions),
                "format": "docker",
                "repository": repo,
                "contentSelector": selector_name(project),
            }
        )
    return bodies


def role_id(project, policy):
    return "%s%s-%s" % (PROJECT_PREFIX, project, policy)


def role_body(project, policy, cfg):
    rid = role_id(project, policy)
    return {
        "id": rid,
        "name": rid,
        "description": "%s on project %s" % (policy, project),
        "privileges": [b["name"] for b in privilege_bodies(project, policy, cfg)],
        "roles": [],
    }


def pip_role_body(cfg):
    repo = cfg.pypi_repo
    return {
        "id": PIP_ROLE,
        "name": PIP_ROLE,
        "description": "pip install from %s" % repo,
        "privileges": [
            "nx-repository-view-pypi-%s-browse" % repo,
            "nx-repository-view-pypi-%s-read" % repo,
        ],
        "roles": [],
    }


def parse_role(role):
    if not role.startswith(PROJECT_PREFIX):
        return None
    project, _, policy = role[len(PROJECT_PREFIX):].rpartition("-")
    if project and policy in POLICIES:
        return project, policy
    return None
