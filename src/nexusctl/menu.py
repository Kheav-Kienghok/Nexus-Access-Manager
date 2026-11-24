from __future__ import annotations

from . import flows
from .errors import Cancelled, NexusError, ProjectMissing, UsageError

ITEMS = (
    (1, "Create project", lambda ctx: flows.create_project_flow(ctx)),
    (2, "Create user account (full access to one project)", lambda ctx: flows.create_account_flow(ctx, "user")),
    (3, "Create robot account (pull and push to one project)", lambda ctx: flows.create_account_flow(ctx, "robot")),
    (4, "Change the policy of an account", lambda ctx: flows.change_policy_flow(ctx)),
    (5, "List projects", lambda ctx: flows.list_projects(ctx)),
    (6, "List accounts", lambda ctx: flows.list_accounts(ctx)),
    (7, "Reset a password", lambda ctx: flows.reset_password_flow(ctx)),
    (8, "Delete an account", lambda ctx: flows.delete_account_flow(ctx)),
    (9, "Delete a project", lambda ctx: flows.delete_project_flow(ctx)),
    (10, "Check connection and setup", lambda ctx: flows.check_flow(ctx)),
)


def run_menu(ctx):
    io = ctx.io
    handlers = {number: handler for number, _, handler in ITEMS}
    while True:
        io.say()
        io.say("nexusctl  %s as %s" % (ctx.cfg.url, ctx.cfg.admin_user))
        for number, title, _ in ITEMS:
            io.say("  %02d  %s" % (number, title))
        io.say("  00  Exit")
        try:
            answer = io.ask("Choose")
        except Cancelled:
            return 0
        if not answer:
            continue
        if not answer.isdigit():
            io.say("Type a number from the list, for example 03.")
            continue
        number = int(answer)
        if number == 0:
            return 0
        handler = handlers.get(number)
        if handler is None:
            io.say("No item %s." % answer)
            continue
        try:
            handler(ctx)
        except Cancelled as exc:
            io.say("Cancelled: %s" % exc)
        except (UsageError, ProjectMissing, NexusError) as exc:
            io.say("Error: %s" % exc)
