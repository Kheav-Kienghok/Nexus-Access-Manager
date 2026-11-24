from __future__ import annotations

import argparse
import ssl

from . import __version__, flows
from .config import load_config
from .errors import Cancelled, NexusError, ProjectMissing, UsageError
from .menu import run_menu
from .policies import POLICIES, PRESETS, SUMMARY, parse_policies
from .util import IO, table

DESCRIPTION = """\
Manage Nexus access for Docker projects and the Python mirror.

A project is an image namespace: images are named <project>/<image>. Every
account gets policies on one project: read, pull, push, update, delete.
Robot accounts default to pull + push, user accounts to full access.
Every account can also pip install from the Python mirror (--no-pip to skip).

Run without a command for the numbered interactive menu."""

EPILOG = """\
examples:
  nexusctl                                          interactive menu
  nexusctl project create speedtest
  nexusctl robot create --project speedtest         pull + push (CI)
  nexusctl user create alice --project speedtest    full access
  nexusctl user create bob --project speedtest --policy read,pull
  nexusctl account policy bob --project speedtest --add push
  nexusctl account list --project speedtest
  nexusctl account password robot-speedtest
  nexusctl policies

connection (environment variables, a .env file, or the options above):
  NEXUS_URL             https://nexus.example.com
  NEXUS_ADMIN_USER      admin (default)
  NEXUS_ADMIN_PASSWORD  admin password (asked if missing)
  NEXUS_INSECURE=1      skip TLS verification
  NEXUS_CACERT=FILE     CA file to trust
  NEXUS_RESOLVE=IP      connect to this IP, keep the URL name (127.0.0.1 on the Nexus VM)
"""


def _common():
    parent = argparse.ArgumentParser(add_help=False)
    group = parent.add_argument_group("connection and behaviour")
    skip = argparse.SUPPRESS
    group.add_argument("--env-file", metavar="FILE", default=skip, help="read settings from this file (default ./.env and ~/.config/nexusctl/env)")
    group.add_argument("--url", metavar="URL", default=skip, help="Nexus URL (env NEXUS_URL)")
    group.add_argument("--user", metavar="NAME", default=skip, help="Nexus admin user (env NEXUS_ADMIN_USER, default admin)")
    group.add_argument("--insecure", action="store_true", default=skip, help="do not verify the TLS certificate (env NEXUS_INSECURE=1)")
    group.add_argument("--cacert", metavar="FILE", default=skip, help="CA file to trust (env NEXUS_CACERT)")
    group.add_argument("--resolve", metavar="IP", default=skip, help="connect to this IP but keep the URL host name (env NEXUS_RESOLVE)")
    group.add_argument("-y", "--yes", action="store_true", default=skip, help="do not ask for confirmation")
    return parent


def _account_options(parser, robot):
    parser.add_argument("--project", metavar="NAME", help="project the account works on (asked if missing)")
    parser.add_argument(
        "--policy",
        metavar="LIST",
        help="comma separated policies: %s, or all (default: %s)"
        % (", ".join(POLICIES), ",".join(PRESETS["robot" if robot else "user"])),
    )
    parser.add_argument("--no-pip", action="store_true", help="do not include pip pull from the Python mirror")
    parser.add_argument("--create-project", action="store_true", help="create the project if it does not exist")
    parser.add_argument("--email", metavar="ADDRESS", help="email address stored in Nexus (default <username>@NEXUS_EMAIL_DOMAIN)")
    parser.add_argument("--password-stdin", action="store_true", help="read the password from one line on stdin instead of generating it")


def build_parser():
    common = _common()
    parser = argparse.ArgumentParser(
        prog="nexusctl",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    parser.add_argument("--version", action="version", version="nexusctl " + __version__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND", title="commands")

    def add(name, help_text, **kw):
        return sub.add_parser(name, help=help_text, description=help_text, parents=[common],
                              formatter_class=argparse.RawDescriptionHelpFormatter, **kw)

    add("menu", "interactive numbered menu (default when no command is given)")
    add("check", "check the connection, the login and the repositories nexusctl needs")
    add("policies", "show the policies and what each one allows")

    project = add("project", "create, list and delete projects")
    psub = project.add_subparsers(dest="sub", metavar="ACTION", required=True)
    p = psub.add_parser("create", help="create a project", parents=[common])
    p.add_argument("name", help="project name: lowercase letters, digits, dashes")
    psub.add_parser("list", help="list projects and who has access", parents=[common])
    p = psub.add_parser("delete", help="delete the access rules of a project (images stay)", parents=[common])
    p.add_argument("name")

    user = add("user", "create a user account")
    usub = user.add_subparsers(dest="sub", metavar="ACTION", required=True)
    p = usub.add_parser("create", help="create a user (default policies: all)", parents=[common])
    p.add_argument("username", nargs="?", help="login name (asked if missing)")
    _account_options(p, robot=False)

    robot = add("robot", "create a robot account for CI")
    rsub = robot.add_subparsers(dest="sub", metavar="ACTION", required=True)
    p = rsub.add_parser("create", help="create a robot (default policies: pull,push)", parents=[common])
    p.add_argument("--name", metavar="USERNAME", help="robot login name (default robot-<project>)")
    _account_options(p, robot=True)

    account = add("account", "list, show and change accounts created by nexusctl")
    asub = account.add_subparsers(dest="sub", metavar="ACTION", required=True)
    p = asub.add_parser("list", help="list accounts with their project and policies", parents=[common])
    p.add_argument("--project", metavar="NAME", help="only accounts of this project")
    p = asub.add_parser("show", help="show one account", parents=[common])
    p.add_argument("username")
    p = asub.add_parser("policy", help="change the policies of an account on a project", parents=[common])
    p.add_argument("username", nargs="?")
    p.add_argument("--project", metavar="NAME")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--set", metavar="LIST", help="replace the policies with this list (empty access: none)")
    mode.add_argument("--add", metavar="LIST", help="add these policies")
    mode.add_argument("--remove", metavar="LIST", help="remove these policies")
    p = asub.add_parser("pip", help="turn pip pull from the Python mirror on or off", parents=[common])
    p.add_argument("username")
    p.add_argument("state", choices=("on", "off"))
    p = asub.add_parser("password", help="reset the password (generated unless --password-stdin)", parents=[common])
    p.add_argument("username", nargs="?")
    p.add_argument("--password-stdin", action="store_true")
    p = asub.add_parser("delete", help="delete an account", parents=[common])
    p.add_argument("username", nargs="?")
    return parser


def _config(args):
    overrides = {
        "url": getattr(args, "url", None),
        "admin_user": getattr(args, "user", None),
        "insecure": True if getattr(args, "insecure", False) else None,
        "cacert": getattr(args, "cacert", None),
        "resolve": getattr(args, "resolve", None),
    }
    return load_config(env_file=getattr(args, "env_file", None), overrides=overrides)


def _policies(io):
    rows = [(i, name, SUMMARY[name]) for i, name in enumerate(POLICIES, 1)]
    io.say(table(("#", "POLICY", "ALLOWS"), rows))
    io.say()
    io.say("defaults: robot = %s, user = %s" % (",".join(PRESETS["robot"]), ",".join(PRESETS["user"])))
    io.say("every account also gets pip pull from the Python mirror unless --no-pip is given")
    return 0


def _password(args, io):
    if getattr(args, "password_stdin", False):
        value = io.stdin.readline().strip()
        if not value:
            raise UsageError("--password-stdin: stdin was empty")
        return value
    return None


def _create(args, ctx, kind):
    policies = parse_policies(args.policy) if args.policy else None
    flows.create_account_flow(
        ctx,
        kind,
        username=getattr(args, "username", None) or getattr(args, "name", None),
        project=args.project,
        policies=policies,
        pip=False if args.no_pip else None,
        password=_password(args, ctx.io),
        create_project=args.create_project,
        email=args.email,
    )
    return 0


def _account(args, ctx):
    sub = args.sub
    if sub == "list":
        flows.list_accounts(ctx, args.project)
    elif sub == "show":
        flows.show_account(ctx, args.username)
    elif sub == "policy":
        if args.set is not None:
            mode, text = "set", args.set
        elif args.add is not None:
            mode, text = "add", args.add
        elif args.remove is not None:
            mode, text = "remove", args.remove
        else:
            mode, text = None, None
        policies = None
        if text is not None:
            policies = () if text.strip().lower() == "none" else parse_policies(text)
        flows.change_policy_flow(ctx, args.username, args.project, mode, policies)
    elif sub == "pip":
        ctx.accounts.set_pip(args.username, args.state == "on")
        ctx.io.say("pip pull for %s: %s" % (args.username, args.state))
    elif sub == "password":
        flows.reset_password_flow(ctx, args.username, _password(args, ctx.io))
    elif sub == "delete":
        flows.delete_account_flow(ctx, args.username)
    return 0


def _run(args, io, parser):
    command = args.command
    if command == "policies":
        return _policies(io)
    if command is None and not io.interactive:
        io.say(parser.format_help())
        return 0

    ctx = flows.build_context(_config(args), io, assume_yes=getattr(args, "yes", False))

    if command in (None, "menu"):
        return run_menu(ctx)
    if command == "check":
        return 0 if flows.check_flow(ctx) else 1
    if command == "project":
        if args.sub == "create":
            flows.create_project_flow(ctx, args.name)
        elif args.sub == "list":
            flows.list_projects(ctx)
        else:
            flows.delete_project_flow(ctx, args.name)
        return 0
    if command == "user":
        return _create(args, ctx, "user")
    if command == "robot":
        return _create(args, ctx, "robot")
    if command == "account":
        return _account(args, ctx)
    io.say(parser.format_help())
    return 2


def _explain(exc):
    if exc.status == 401:
        return "Nexus rejected the admin login (401). Check NEXUS_ADMIN_USER and NEXUS_ADMIN_PASSWORD."
    if exc.status == 403:
        return "Nexus says this admin account may not do that (403)."
    return str(exc)


def main(argv=None, io=None):
    io = io or IO()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args, io, parser)
    except KeyboardInterrupt:
        io.say()
        return 130
    except Cancelled as exc:
        io.say("Cancelled: %s" % exc)
        return 1
    except (UsageError, ProjectMissing) as exc:
        io.error("error: %s" % exc)
        return 2
    except NexusError as exc:
        io.error("error: %s" % _explain(exc))
        return 1
    except BrokenPipeError:
        return 0
    except ssl.SSLError as exc:
        io.error("error: TLS failed (%s). Trust the CA with NEXUS_CACERT or use NEXUS_INSECURE=1." % exc)
        return 1
    except OSError as exc:
        io.error("error: cannot reach Nexus (%s). Check NEXUS_URL and NEXUS_RESOLVE." % exc)
        return 1
