# How it works

Nexus has no Harbor-style project object. `nexusctl` builds the same thing from three Nexus features, using the REST API (`/service/rest/v1`) with the admin account.

```text
project "speedtest"
  = content selector   path =^ "/v2/speedtest/"        (which images)
  + privileges         selector x repository x actions (what may be done)
  + roles              one per policy                   (bundles of privileges)

account "robot-speedtest"
  = Nexus user         firstName = nexusctl, lastName = robot
  + roles              proj-speedtest-pull, proj-speedtest-push, nexusctl-pip-pull
```

## Project

Images of a project are named `<project>/<image>`, so the Docker registry path starts with `/v2/<project>/`. The content selector matches that prefix, which covers every manifest, tag and layer of the project. Privileges attach the selector to a repository and a set of actions. Roles bundle the privileges of one policy.

## Account

An account is a normal Nexus user. `nexusctl` marks the users it creates with `firstName = nexusctl` and `lastName = user` or `robot`. That mark is how it recognises its own accounts:

- `account list` shows only marked accounts.
- `account policy`, `password`, `pip` and `delete` refuse any other user, so the `admin` and `anonymous` users and people created in the Nexus UI cannot be changed by mistake.

A robot account is not a special Nexus type. It is a user with a long generated password, named `robot-<project>` by default. As far as I know, Nexus user tokens are a Pro feature, so Community has no token-based robots.

## Flows

Creating an account (menu `02` and `03`, or `user create` and `robot create`):

1. Pick the project. If none exists, `nexusctl` asks to create one. With `--project NAME` for a project that does not exist, it asks in a terminal, and fails with a hint in a script unless `--create-project` is given.
2. Ask for the username (robots default to `robot-<project>`).
3. Ask for the policies, with the default for the account type pre-selected.
4. Ask whether to include pip pull, and whether to generate the password.
5. Show a summary, ask for confirmation, create the user, print the password once and the `docker login` and `pip` commands.

Changing a policy replaces, adds or removes the `proj-<project>-<policy>` roles of that project on the user. Roles of other projects stay as they are.

Deleting a project removes its roles from every user, then deletes the roles, privileges and selector. Images are not touched.

## Connection

All calls go to `NEXUS_URL` with HTTP basic auth as the admin user. Behind Caddy on the Nexus VM, set `NEXUS_RESOLVE=127.0.0.1` to connect to the local Caddy while keeping the real name for the Host header and the certificate check, the same as `curl --resolve`.

## What is not covered

- Project quotas, a project page and an audit view like Harbor's.
- Per-project Python packages: the pip access is read-only and applies to the whole Python repository.
- The Docker catalog and `docker search` are not filtered per project by Nexus.
