from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from .accounts import AccountService
from .client import NexusClient
from .config import Config
from .errors import Cancelled, NexusError, ProjectMissing, UsageError
from .policies import POLICIES, PRESETS, SUMMARY, parse_policies
from .projects import ProjectService
from .util import (
    IO,
    PROJECT_RE,
    table,
    validate_project,
    validate_username,
)


@dataclass
class Context:
    cfg: Config
    client: NexusClient
    projects: ProjectService
    accounts: AccountService
    io: IO
    assume_yes: bool = False


def build_context(cfg, io, assume_yes=False):
    cfg.validate()
    if not cfg.admin_password:
        if not io.interactive:
            raise UsageError("set NEXUS_ADMIN_PASSWORD (or NEW_ADMIN_PASSWORD) for the Nexus admin user")
        cfg.admin_password = io.secret("Password for %s on %s" % (cfg.admin_user, cfg.url))
    client = NexusClient(cfg)
    projects = ProjectService(client, cfg)
    return Context(cfg, client, projects, AccountService(client, cfg, projects), io, assume_yes)


def confirm_action(ctx, prompt, default=True, destructive=False):
    if ctx.assume_yes:
        return True
    if not ctx.io.interactive:
        if destructive:
            raise UsageError("add --yes to confirm: %s" % prompt)
        return True
    return ctx.io.confirm(prompt, default)


def describe(account):
    if not account.projects:
        return "no project"
    return "; ".join("%s: %s" % (p, ",".join(v)) for p, v in account.projects.items())


def ask_policies(io, default, allow_none=False):
    io.say("Policies:")
    for i, name in enumerate(POLICIES, 1):
        io.say("  %d  %-7s %s" % (i, name, SUMMARY[name]))
    default_text = ",".join(default)
    hint = "Choose numbers or names separated by commas, or all"
    if allow_none:
        hint += ", or none to remove access"
    while True:
        answer = io.ask(hint, default_text)
        if allow_none and answer.lower() == "none":
            return ()
        try:
            return parse_policies(answer)
        except UsageError as exc:
            io.say(str(exc))


def create_project_flow(ctx, name=None):
    io = ctx.io
    if name is None:
        while True:
            candidate = io.ask("Project name (lowercase letters, digits, dashes; images are named <project>/<image>)")
            try:
                name = validate_project(candidate)
                break
            except UsageError as exc:
                io.say(str(exc))
    else:
        validate_project(name)

    if ctx.projects.exists(name):
        io.say("Project %s already exists." % name)
        return name

    created, _ = ctx.projects.create(name)
    io.say("Created project %s (%d Nexus objects)." % (name, len(created)))
    io.say("  images: %s/<image>:<tag>" % name)
    io.say("  policies available: %s" % ", ".join(POLICIES))
    return name


def choose_project(ctx, name=None, create_missing=False, allow_create=True, prompt="Project"):
    io = ctx.io
    names = ctx.projects.names()

    if name:
        if name in names:
            return name
        validate_project(name)
        if not allow_create:
            raise UsageError("project %s does not exist" % name)
        if create_missing:
            return create_project_flow(ctx, name)
        if io.interactive:
            io.say("Project %s does not exist." % name)
            if io.confirm("Create it now?", True):
                return create_project_flow(ctx, name)
            raise Cancelled("project not created")
        raise UsageError(
            "project %s does not exist: create it with 'nexusctl project create %s' or pass --create-project" % (name, name)
        )

    if not io.interactive:
        raise UsageError("give --project NAME")

    if not names:
        if not allow_create:
            raise UsageError("no project exists yet")
        io.say("No project exists yet.")
        if not io.confirm("Create one now?", True):
            raise Cancelled("a project is needed first")
        return create_project_flow(ctx)

    io.say("Projects:")
    for i, item in enumerate(names, 1):
        io.say("  %d  %s" % (i, item))
    if allow_create:
        io.say("  n  create a new project")
    default = "1" if len(names) == 1 else None
    while True:
        answer = io.ask("%s (number or name%s)" % (prompt, ", n for new" if allow_create else ""), default)
        if not answer:
            continue
        if allow_create and answer.lower() in ("n", "new"):
            return create_project_flow(ctx)
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            return names[int(answer) - 1]
        if answer in names:
            return answer
        if allow_create and PROJECT_RE.match(answer):
            if io.confirm("Project %s does not exist. Create it?" % answer, True):
                return create_project_flow(ctx, answer)
            continue
        io.say("Unknown project %r." % answer)


def choose_account(ctx, username=None, prompt="Account"):
    io = ctx.io
    if username:
        ctx.accounts.get(username)
        return username
    if not io.interactive:
        raise UsageError("give the username")
    accounts = ctx.accounts.list()
    if not accounts:
        raise UsageError("no accounts created by nexusctl yet")
    io.say("Accounts:")
    for i, acc in enumerate(accounts, 1):
        io.say("  %d  %-26s %-6s %s" % (i, acc.id, acc.kind, describe(acc)))
    while True:
        answer = io.ask("%s (number or name)" % prompt)
        if answer.isdigit() and 1 <= int(answer) <= len(accounts):
            return accounts[int(answer) - 1].id
        if answer in {a.id for a in accounts}:
            return answer
        io.say("Unknown account %r." % answer)


def ask_password(ctx, kind):
    io = ctx.io
    if not io.interactive:
        return None
    if io.confirm("Generate a strong password?", True):
        return None
    while True:
        first = io.secret("Password")
        if len(first) < 8:
            io.say("Use at least 8 characters.")
            continue
        if first == io.secret("Repeat password"):
            return first
        io.say("The passwords do not match.")


def print_created(ctx, created):
    io, cfg = ctx.io, ctx.cfg
    io.say()
    io.say("Created %s account" % created.kind)
    io.say("  username  %s" % created.username)
    io.say("  password  %s   (shown once, store it now)" % created.password)
    io.say("  project   %s" % created.project)
    io.say("  policies  %s" % ", ".join(created.policies))
    io.say("  pip       %s" % ("pull from %s" % cfg.pypi_repo if created.pip else "no"))
    io.say()
    io.say("Use it")
    host = cfg.host
    if any(p in created.policies for p in ("push", "update", "delete")):
        io.say("  docker login %s:%d -u %s" % (host, cfg.push_port, created.username))
        io.say("  docker push %s:%d/%s/<image>:<tag>" % (host, cfg.push_port, created.project))
    if "pull" in created.policies:
        io.say("  docker login %s:%d -u %s" % (host, cfg.pull_port, created.username))
        io.say("  docker pull %s:%d/%s/<image>:<tag>" % (host, cfg.pull_port, created.project))
    if created.pip:
        netloc = urlsplit(cfg.url).netloc
        io.say(
            "  pip install --index-url %s://%s:<password>@%s%s/repository/%s/simple <package>"
            % (cfg.scheme, created.username, netloc, cfg.base_path, cfg.pypi_repo)
        )


def create_account_flow(
    ctx,
    kind,
    username=None,
    project=None,
    policies=None,
    pip=None,
    password=None,
    create_project=False,
    email=None,
):
    io = ctx.io
    label = "robot account" if kind == "robot" else "user account"

    project = choose_project(ctx, project, create_missing=create_project)

    if not username:
        if kind == "robot":
            default = "robot-%s" % project
            username = io.ask("Robot account name", default) if io.interactive else default
        elif io.interactive:
            username = io.ask("Username")
        else:
            raise UsageError("give the username")
    validate_username(username)
    if ctx.accounts._find(username) is not None:
        raise UsageError("user %s already exists, change its policy with 'nexusctl account policy'" % username)

    if policies is None:
        default = PRESETS[kind]
        policies = ask_policies(io, default) if io.interactive else default

    if pip is None:
        pip = io.confirm("Include pip pull from the Python mirror (%s)?" % ctx.cfg.pypi_repo, True) if io.interactive else True

    if password is None:
        password = ask_password(ctx, kind)

    io.say()
    io.say("About to create a %s" % label)
    io.say("  username  %s" % username)
    io.say("  project   %s" % project)
    io.say("  policies  %s" % ", ".join(policies))
    io.say("  pip       %s" % ("yes" if pip else "no"))
    if not confirm_action(ctx, "Create it?", True):
        raise Cancelled("nothing created")

    created = ctx.accounts.create(kind, username, project, policies, pip=pip, password=password, email=email)
    print_created(ctx, created)
    return created


def change_policy_flow(ctx, username=None, project=None, mode=None, policies=None):
    io = ctx.io
    username = choose_account(ctx, username)
    account = ctx.accounts.get(username)

    if project is None and not io.interactive:
        raise UsageError("give --project NAME")
    project = choose_project(ctx, project, allow_create=False, prompt="Project to change")

    if mode is None or policies is None:
        if not io.interactive:
            raise UsageError("give --set, --add or --remove with a policy list")
        current = account.projects.get(project, [])
        io.say("Current policies of %s on %s: %s" % (username, project, ",".join(current) or "none"))
        policies = ask_policies(io, current or PRESETS[account.kind], allow_none=True)
        mode = "set"

    result = ctx.accounts.change_policies(username, project, mode, policies)
    io.say("%s now has on %s: %s" % (username, project, ", ".join(result) or "no access"))
    return result


def list_projects(ctx):
    names = ctx.projects.names()
    if not names:
        ctx.io.say("No projects yet. Create one with: nexusctl project create <name>")
        return names
    accounts = ctx.accounts.list()
    rows = []
    for name in names:
        members = [a.id for a in accounts if name in a.projects]
        rows.append((name, "%s/<image>" % name, len(members), ", ".join(members)))
    ctx.io.say(table(("PROJECT", "IMAGES", "ACCOUNTS", "WHO"), rows))
    return names


def list_accounts(ctx, project=None):
    accounts = ctx.accounts.list(project)
    if not accounts:
        ctx.io.say("No accounts created by nexusctl%s." % (" for project %s" % project if project else ""))
        return accounts
    rows = []
    for acc in accounts:
        pip = "yes" if acc.pip else "no"
        projects = acc.projects
        if project:
            projects = {project: projects[project]}
        if not projects:
            rows.append((acc.id, acc.kind, "-", "-", pip, acc.status))
        for name, items in projects.items():
            rows.append((acc.id, acc.kind, name, ",".join(items), pip, acc.status))
    ctx.io.say(table(("USERNAME", "TYPE", "PROJECT", "POLICIES", "PIP", "STATUS"), rows))
    return accounts


def show_account(ctx, username):
    acc = ctx.accounts.get(username)
    io = ctx.io
    io.say("username  %s" % acc.id)
    io.say("type      %s" % acc.kind)
    io.say("status    %s" % acc.status)
    io.say("email     %s" % acc.email)
    io.say("pip       %s" % ("pull from %s" % ctx.cfg.pypi_repo if acc.pip else "no"))
    if not acc.projects:
        io.say("projects  none")
    for name, items in acc.projects.items():
        io.say("project   %s: %s" % (name, ", ".join(items)))
    return acc


def reset_password_flow(ctx, username=None, password=None):
    io = ctx.io
    username = choose_account(ctx, username)
    if password is None and io.interactive:
        password = ask_password(ctx, "user")
    new = ctx.accounts.reset_password(username, password)
    io.say("New password for %s: %s   (shown once, store it now)" % (username, new))
    return new


def delete_account_flow(ctx, username=None):
    username = choose_account(ctx, username, prompt="Account to delete")
    if not confirm_action(ctx, "Delete account %s?" % username, False, destructive=True):
        raise Cancelled("account kept")
    ctx.accounts.delete(username)
    ctx.io.say("Deleted account %s." % username)


def delete_project_flow(ctx, name=None):
    io = ctx.io
    name = choose_project(ctx, name, allow_create=False, prompt="Project to delete")
    members = [a.id for a in ctx.accounts.list(name)]
    if members:
        io.say("Accounts with access to %s lose it: %s" % (name, ", ".join(members)))
    io.say("Images stay in Nexus; only the access rules are removed.")
    if not confirm_action(ctx, "Delete project %s?" % name, False, destructive=True):
        raise Cancelled("project kept")
    ctx.projects.delete(name)
    io.say("Deleted project %s." % name)


def check_flow(ctx):
    io, cfg = ctx.io, ctx.cfg
    ok = True

    def report(good, text):
        nonlocal ok
        ok = ok and good
        io.say("  [%s] %s" % ("ok" if good else "!!", text))

    io.say("Checking %s" % cfg.url)
    try:
        ctx.client.status()
        report(True, "Nexus answers")
    except NexusError as exc:
        report(False, "Nexus status: %s" % exc)

    try:
        ctx.client.roles()
        report(True, "login works as %s" % cfg.admin_user)
    except NexusError as exc:
        report(False, "login as %s failed (%s)" % (cfg.admin_user, exc.status))
        return False

    names = {r.get("name") for r in ctx.client.repositories()}
    for label, repo in (("docker pull repository", cfg.pull_repo), ("docker push repository", cfg.push_repo), ("python mirror", cfg.pypi_repo)):
        report(repo in names, "%s %s %s" % (label, repo, "found" if repo in names else "missing"))

    try:
        realms = ctx.client.realms()
        report("DockerToken" in realms, "Docker Bearer Token Realm %s" % ("active" if "DockerToken" in realms else "not active (docker login will fail)"))
    except NexusError as exc:
        report(False, "realms: %s" % exc)

    io.say("  projects: %d, accounts: %d" % (len(ctx.projects.names()), len(ctx.accounts.list())))
    return ok
