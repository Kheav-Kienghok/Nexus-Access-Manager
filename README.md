# Nexus Access Manager

A small command line tool and numbered menu to manage access in Sonatype Nexus for Docker images and the Python mirror. It creates projects, user accounts and robot accounts, and gives each of them only the policies they need on one project.

```text
$ nexusctl
nexusctl  https://nexus.example.com as admin
  01  Create project
  02  Create user account (full access to one project)
  03  Create robot account (pull and push to one project)
  04  Change the policy of an account
  05  List projects
  06  List accounts
  07  Reset a password
  08  Delete an account
  09  Delete a project
  10  Check connection and setup
  00  Exit
Choose:
```

- A project is an image namespace: images are named `<project>/<image>`.
- A **robot account** gets `pull` and `push` on one project by default, for CI.
- A **user account** gets full access (`read`, `pull`, `push`, `update`, `delete`) on one project by default.
- Every account can also `pip install` from the Nexus Python mirror (leave it out with `--no-pip`).
- No project yet? The tool asks to create one.
- Passwords are generated and shown once. Only accounts created by `nexusctl` can be changed or deleted by it.

Pure Python 3.9+, no dependencies. It talks to the Nexus REST API.

## Requirements

- Nexus Repository 3 with the Docker repositories `docker-all` (group, pull) and `docker-hosted` (push) and the Python repository `pypi-all`. The `nexus-pypi-proxy` project sets all of this up, including Caddy on ports 5000 (pull) and 5002 (push). Other names work through the `NEXUS_*_REPO` settings.
- The Docker Bearer Token Realm active in Nexus (`nexusctl check` tells you).
- The Nexus admin password.

## Install

```bash
# Run from the source folder without installing
./bin/nexusctl --help

# Or install into a virtual environment
python3 -m venv venv
./venv/bin/pip install .
./venv/bin/nexusctl --help

# Or install for your user with pipx
pipx install .
```

## Configure

Copy `.env.example` to `.env` and fill in the values, or use environment variables or options.

```bash
cp .env.example .env
vi .env
```

```text
NEXUS_URL=https://nexus.example.com
NEXUS_ADMIN_USER=admin
NEXUS_ADMIN_PASSWORD=<admin-password>
```

Leave `NEXUS_ADMIN_PASSWORD` empty to be asked for it in a terminal. `nexusctl` also reads `NEW_ADMIN_PASSWORD`, so it works from the folder of the `nexus-pypi-proxy` project.

On the Nexus VM, Nexus is only reachable through Caddy. Connect to the local Caddy but keep the real name, and trust its CA:

```text
NEXUS_URL=https://nexus.example.com
NEXUS_RESOLVE=127.0.0.1
NEXUS_CACERT=/home/ubuntu/nexus-pypi-proxy/certs/ca.crt
```

`./scripts/server/tls.sh export` in `nexus-pypi-proxy` writes that CA file. For a quick local test use `NEXUS_INSECURE=1` instead of `NEXUS_CACERT`.

```bash
# Check the connection, the login and the repositories
nexusctl check
```

## Quick start

```bash
# Open the numbered menu
nexusctl

# Or do the same with commands: create a project (images will be named speedtest/<image>)
nexusctl project create speedtest

# Robot account for CI: pull + push on speedtest, plus pip pull
nexusctl robot create --project speedtest

# A person with full access to speedtest
nexusctl user create alice --project speedtest

# A person who can only read and pull
nexusctl user create bob --project speedtest --policy read,pull

# Give bob push later
nexusctl account policy bob --project speedtest --add push

# Who has what
nexusctl account list

# New password for the robot
nexusctl account password robot-speedtest
```

## The menu

```text
01  Create project
02  Create user account (full access to one project)
03  Create robot account (pull and push to one project)
04  Change the policy of an account
05  List projects
06  List accounts
07  Reset a password
08  Delete an account
09  Delete a project
10  Check connection and setup
00  Exit
```

Creating a robot account when no project exists (real session):

```text
Choose: 03
No project exists yet.
Create one now? (Y/n): 
Project name (lowercase letters, digits, dashes; images are named <project>/<image>): speedtest
Created project speedtest (12 Nexus objects).
  images: speedtest/<image>:<tag>
  policies available: read, pull, push, update, delete
Robot account name [robot-speedtest]: 
Policies:
  1  read    view images in the Nexus UI and search
  2  pull    docker pull
  3  push    docker push (new tags, and overwriting a tag such as latest)
  4  update  modify or overwrite existing tags in the UI or API
  5  delete  delete tags and layers
Choose numbers or names separated by commas, or all [pull,push]: 
Include pip pull from the Python mirror (pypi-all)? (Y/n): 
Generate a strong password? (Y/n): 

About to create a robot account
  username  robot-speedtest
  project   speedtest
  policies  pull, push
  pip       yes
Create it? (Y/n): 

Created robot account
  username  robot-speedtest
  password  <generated>   (shown once, store it now)
  project   speedtest
  policies  pull, push
  pip       pull from pypi-all

Use it
  docker login nexus.example.com:5002 -u robot-speedtest
  docker push nexus.example.com:5002/speedtest/<image>:<tag>
  docker login nexus.example.com:5000 -u robot-speedtest
  docker pull nexus.example.com:5000/speedtest/<image>:<tag>
  pip install --index-url https://robot-speedtest:<password>@nexus.example.com/repository/pypi-all/simple <package>
```

Listing accounts:

```text
Choose: 06
USERNAME         TYPE   PROJECT    POLICIES                      PIP  STATUS
---------------  -----  ---------  ----------------------------  ---  ------
robot-speedtest  robot  speedtest  pull,push                     yes  active
alice            user   speedtest  read,pull,push,update,delete  yes  active
```

## Policies

| Policy | Allows |
|--------|--------|
| `read` | view images in the Nexus UI and search |
| `pull` | `docker pull` |
| `push` | `docker push`, including overwriting a tag such as `latest` |
| `update` | modify or overwrite existing tags in the UI or API |
| `delete` | delete tags and layers |

Defaults: robot `pull,push`, user all five. Show them with `nexusctl policies`. Details and the Nexus objects behind them: [docs/policies.md](docs/policies.md).

## Commands

| Command | Does |
|---------|------|
| `nexusctl` or `nexusctl menu` | numbered interactive menu |
| `nexusctl check` | check connection, login and repositories |
| `nexusctl policies` | show the policies |
| `nexusctl project create NAME` | create a project |
| `nexusctl project list` | list projects and who has access |
| `nexusctl project delete NAME` | remove a project's access rules (images stay) |
| `nexusctl user create [USERNAME]` | create a user, default policies: all |
| `nexusctl robot create [--name NAME]` | create a robot, default policies: pull,push |
| `nexusctl account list [--project NAME]` | list accounts, projects and policies |
| `nexusctl account show USERNAME` | show one account |
| `nexusctl account policy USERNAME --project NAME --set\|--add\|--remove LIST` | change policies |
| `nexusctl account pip USERNAME on\|off` | turn pip pull on or off |
| `nexusctl account password [USERNAME]` | reset a password |
| `nexusctl account delete [USERNAME]` | delete an account |

Options for the account commands: `--project`, `--policy`, `--no-pip`, `--create-project`, `--email`, `--password-stdin`. Connection options for every command: `--env-file`, `--url`, `--user`, `--insecure`, `--cacert`, `--resolve`, `-y/--yes`. When a value is missing and you are in a terminal, the tool asks for it. In a script it fails with exit code 2 and says what to add.

Full help for every command: [docs/usage.md](docs/usage.md), or `nexusctl COMMAND --help`.

## Use the accounts

```bash
# Push (robot or user with push), port 5002
echo '<password>' | docker login nexus.example.com:5002 -u robot-speedtest --password-stdin
docker push nexus.example.com:5002/speedtest/api:1.0

# Pull, port 5000
docker login nexus.example.com:5000 -u robot-speedtest
docker pull nexus.example.com:5000/speedtest/api:1.0

# Python packages through the mirror
pip install --index-url https://robot-speedtest:<password>@nexus.example.com/repository/pypi-all/simple requests
```

GitLab CI with masked variables `NEXUS_ROBOT_USER` and `NEXUS_ROBOT_PASS`:

```yaml
build:
  script:
    - echo "$NEXUS_ROBOT_PASS" | docker login nexus.example.com:5002 -u "$NEXUS_ROBOT_USER" --password-stdin
    - docker build -t nexus.example.com:5002/speedtest/api:$CI_COMMIT_SHORT_SHA .
    - docker push nexus.example.com:5002/speedtest/api:$CI_COMMIT_SHORT_SHA
```

## Project layout

```text
nexusctl/
├── README.md
├── pyproject.toml          package and the nexusctl command
├── .env.example            settings template
├── bin/nexusctl            run from the source folder
├── src/nexusctl/
│   ├── cli.py              command line parser and dispatch
│   ├── menu.py             numbered interactive menu
│   ├── flows.py            guided flows shared by the menu and the commands
│   ├── projects.py         project = selector + privileges + roles
│   ├── accounts.py         users and robot accounts
│   ├── policies.py         policy to Nexus privilege mapping and names
│   ├── client.py           Nexus REST client (HTTP, TLS, --resolve)
│   ├── config.py           settings from options, environment and .env files
│   ├── util.py             validation, prompts, tables
│   └── errors.py
├── tests/                  60+ tests against an in-memory fake Nexus
│   ├── fake_nexus.py
│   └── test_*.py
└── docs/
    ├── usage.md            every command with its help text
    ├── policies.md         policies and the Nexus objects they create
    ├── how-it-works.md
    └── troubleshooting.md
```

## Good to know

- `nexusctl` manages only accounts it created. It marks them in Nexus (`firstName = nexusctl`) and refuses to change or delete other users such as `admin`.
- Deleting a project removes access rules and detaches accounts. Images stay in Nexus.
- On Nexus Community there are no user tokens, as far as I know, so a robot account is a normal user with a long random password. Rotate it with `nexusctl account password`.
- Roles only limit users who log in. Turn anonymous access off in Nexus for the isolation to hold.
- The `docker-all` and `docker-hosted` repository names, the ports and the Python repository are settings, see [docs/usage.md](docs/usage.md).
- The content selector path format (`/v2/<project>/`) should be checked once on your Nexus version, see [docs/troubleshooting.md](docs/troubleshooting.md).

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```
