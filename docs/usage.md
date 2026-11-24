# Command reference

Every command also works without the menu, so it can run in scripts and CI. The output below is the real `--help` text.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | done |
| 1 | Nexus or network error, a check failed, or you cancelled |
| 2 | wrong usage: bad option, missing project or username, `--yes` needed |
| 130 | interrupted with Ctrl+C |

## Settings

Settings come from, in this order of priority: command line options, environment variables, `./.env`, `~/.config/nexusctl/env`.

| Variable | Option | Default | Meaning |
|----------|--------|---------|---------|
| `NEXUS_URL` | `--url` | required | for example `https://nexus.example.com` |
| `NEXUS_ADMIN_USER` | `--user` | `admin` | Nexus admin account |
| `NEXUS_ADMIN_PASSWORD` | | asked if missing | admin password (`NEW_ADMIN_PASSWORD` is accepted too) |
| `NEXUS_INSECURE` | `--insecure` | off | skip TLS verification |
| `NEXUS_CACERT` | `--cacert` | system store | CA file to trust |
| `NEXUS_RESOLVE` | `--resolve` | none | connect to this IP, keep the URL name |
| `NEXUS_PULL_REPO` | | `docker-all` | Docker repository used for pull |
| `NEXUS_PUSH_REPO` | | `docker-hosted` | Docker repository used for push, update and delete |
| `NEXUS_PYPI_REPO` | | `pypi-all` | Python repository used for pip pull |
| `NEXUS_PULL_PORT` | | `5000` | port shown in the `docker pull` hint |
| `NEXUS_PUSH_PORT` | | `5002` | port shown in the `docker push` hint |
| `NEXUS_EMAIL_DOMAIN` | | `example.com` | account emails are `<username>@<domain>` |

## Examples

```bash
# Project, robot for CI, and a person with full access
nexusctl project create speedtest
nexusctl robot create --project speedtest
nexusctl user create alice --project speedtest

# Create the project on the fly
nexusctl robot create --project billing --create-project

# A read-only person without pip access
nexusctl user create bob --project speedtest --policy read,pull --no-pip

# Change policies
nexusctl account policy bob --project speedtest --add push
nexusctl account policy bob --project speedtest --remove read
nexusctl account policy bob --project speedtest --set pull
nexusctl account policy bob --project speedtest --set none

# Look around
nexusctl account list --project speedtest
nexusctl account show robot-speedtest

# Own password instead of a generated one
echo 'a-long-password' | nexusctl user create carol --project speedtest --password-stdin

# Rotate a robot password and delete accounts and projects without questions
nexusctl account password robot-speedtest
nexusctl account delete bob --yes
nexusctl project delete speedtest --yes
```

## Help output

### nexusctl

```text
usage: nexusctl [-h] [--env-file FILE] [--url URL] [--user NAME] [--insecure]
                [--cacert FILE] [--resolve IP] [-y] [--version]
                COMMAND ...

Manage Nexus access for Docker projects and the Python mirror.

A project is an image namespace: images are named <project>/<image>. Every
account gets policies on one project: read, pull, push, update, delete.
Robot accounts default to pull + push, user accounts to full access.
Every account can also pip install from the Python mirror (--no-pip to skip).

Run without a command for the numbered interactive menu.

options:
  -h, --help       show this help message and exit
  --version        show program's version number and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation

commands:
  COMMAND
    menu           interactive numbered menu (default when no command is given)
    check          check the connection, the login and the repositories nexusctl
                   needs
    policies       show the policies and what each one allows
    project        create, list and delete projects
    user           create a user account
    robot          create a robot account for CI
    account        list, show and change accounts created by nexusctl

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
```

### nexusctl menu

```text
usage: nexusctl menu [-h] [--env-file FILE] [--url URL] [--user NAME] [--insecure]
                     [--cacert FILE] [--resolve IP] [-y]

interactive numbered menu (default when no command is given)

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl check

```text
usage: nexusctl check [-h] [--env-file FILE] [--url URL] [--user NAME]
                      [--insecure] [--cacert FILE] [--resolve IP] [-y]

check the connection, the login and the repositories nexusctl needs

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl policies

```text
usage: nexusctl policies [-h] [--env-file FILE] [--url URL] [--user NAME]
                         [--insecure] [--cacert FILE] [--resolve IP] [-y]

show the policies and what each one allows

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl project

```text
usage: nexusctl project [-h] [--env-file FILE] [--url URL] [--user NAME]
                        [--insecure] [--cacert FILE] [--resolve IP] [-y]
                        ACTION ...

create, list and delete projects

positional arguments:
  ACTION
    create         create a project
    list           list projects and who has access
    delete         delete the access rules of a project (images stay)

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl project create

```text
usage: nexusctl project create [-h] [--env-file FILE] [--url URL] [--user NAME]
                               [--insecure] [--cacert FILE] [--resolve IP] [-y]
                               name

positional arguments:
  name             project name: lowercase letters, digits, dashes

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl project list

```text
usage: nexusctl project list [-h] [--env-file FILE] [--url URL] [--user NAME]
                             [--insecure] [--cacert FILE] [--resolve IP] [-y]

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl project delete

```text
usage: nexusctl project delete [-h] [--env-file FILE] [--url URL] [--user NAME]
                               [--insecure] [--cacert FILE] [--resolve IP] [-y]
                               name

positional arguments:
  name

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl user

```text
usage: nexusctl user [-h] [--env-file FILE] [--url URL] [--user NAME] [--insecure]
                     [--cacert FILE] [--resolve IP] [-y]
                     ACTION ...

create a user account

positional arguments:
  ACTION
    create         create a user (default policies: all)

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl user create

```text
usage: nexusctl user create [-h] [--env-file FILE] [--url URL] [--user NAME]
                            [--insecure] [--cacert FILE] [--resolve IP] [-y]
                            [--project NAME] [--policy LIST] [--no-pip]
                            [--create-project] [--email ADDRESS]
                            [--password-stdin]
                            [username]

positional arguments:
  username          login name (asked if missing)

options:
  -h, --help        show this help message and exit
  --project NAME    project the account works on (asked if missing)
  --policy LIST     comma separated policies: read, pull, push, update, delete, or
                    all (default: read,pull,push,update,delete)
  --no-pip          do not include pip pull from the Python mirror
  --create-project  create the project if it does not exist
  --email ADDRESS   email address stored in Nexus (default
                    <username>@NEXUS_EMAIL_DOMAIN)
  --password-stdin  read the password from one line on stdin instead of generating
                    it

connection and behaviour:
  --env-file FILE   read settings from this file (default ./.env and
                    ~/.config/nexusctl/env)
  --url URL         Nexus URL (env NEXUS_URL)
  --user NAME       Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure        do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE     CA file to trust (env NEXUS_CACERT)
  --resolve IP      connect to this IP but keep the URL host name (env
                    NEXUS_RESOLVE)
  -y, --yes         do not ask for confirmation
```

### nexusctl robot

```text
usage: nexusctl robot [-h] [--env-file FILE] [--url URL] [--user NAME]
                      [--insecure] [--cacert FILE] [--resolve IP] [-y]
                      ACTION ...

create a robot account for CI

positional arguments:
  ACTION
    create         create a robot (default policies: pull,push)

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl robot create

```text
usage: nexusctl robot create [-h] [--env-file FILE] [--url URL] [--user NAME]
                             [--insecure] [--cacert FILE] [--resolve IP] [-y]
                             [--name USERNAME] [--project NAME] [--policy LIST]
                             [--no-pip] [--create-project] [--email ADDRESS]
                             [--password-stdin]

options:
  -h, --help        show this help message and exit
  --name USERNAME   robot login name (default robot-<project>)
  --project NAME    project the account works on (asked if missing)
  --policy LIST     comma separated policies: read, pull, push, update, delete, or
                    all (default: pull,push)
  --no-pip          do not include pip pull from the Python mirror
  --create-project  create the project if it does not exist
  --email ADDRESS   email address stored in Nexus (default
                    <username>@NEXUS_EMAIL_DOMAIN)
  --password-stdin  read the password from one line on stdin instead of generating
                    it

connection and behaviour:
  --env-file FILE   read settings from this file (default ./.env and
                    ~/.config/nexusctl/env)
  --url URL         Nexus URL (env NEXUS_URL)
  --user NAME       Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure        do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE     CA file to trust (env NEXUS_CACERT)
  --resolve IP      connect to this IP but keep the URL host name (env
                    NEXUS_RESOLVE)
  -y, --yes         do not ask for confirmation
```

### nexusctl account

```text
usage: nexusctl account [-h] [--env-file FILE] [--url URL] [--user NAME]
                        [--insecure] [--cacert FILE] [--resolve IP] [-y]
                        ACTION ...

list, show and change accounts created by nexusctl

positional arguments:
  ACTION
    list           list accounts with their project and policies
    show           show one account
    policy         change the policies of an account on a project
    pip            turn pip pull from the Python mirror on or off
    password       reset the password (generated unless --password-stdin)
    delete         delete an account

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl account list

```text
usage: nexusctl account list [-h] [--env-file FILE] [--url URL] [--user NAME]
                             [--insecure] [--cacert FILE] [--resolve IP] [-y]
                             [--project NAME]

options:
  -h, --help       show this help message and exit
  --project NAME   only accounts of this project

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl account show

```text
usage: nexusctl account show [-h] [--env-file FILE] [--url URL] [--user NAME]
                             [--insecure] [--cacert FILE] [--resolve IP] [-y]
                             username

positional arguments:
  username

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl account policy

```text
usage: nexusctl account policy [-h] [--env-file FILE] [--url URL] [--user NAME]
                               [--insecure] [--cacert FILE] [--resolve IP] [-y]
                               [--project NAME]
                               [--set LIST | --add LIST | --remove LIST]
                               [username]

positional arguments:
  username

options:
  -h, --help       show this help message and exit
  --project NAME
  --set LIST       replace the policies with this list (empty access: none)
  --add LIST       add these policies
  --remove LIST    remove these policies

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl account pip

```text
usage: nexusctl account pip [-h] [--env-file FILE] [--url URL] [--user NAME]
                            [--insecure] [--cacert FILE] [--resolve IP] [-y]
                            username {on,off}

positional arguments:
  username
  {on,off}

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```

### nexusctl account password

```text
usage: nexusctl account password [-h] [--env-file FILE] [--url URL] [--user NAME]
                                 [--insecure] [--cacert FILE] [--resolve IP] [-y]
                                 [--password-stdin]
                                 [username]

positional arguments:
  username

options:
  -h, --help        show this help message and exit
  --password-stdin

connection and behaviour:
  --env-file FILE   read settings from this file (default ./.env and
                    ~/.config/nexusctl/env)
  --url URL         Nexus URL (env NEXUS_URL)
  --user NAME       Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure        do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE     CA file to trust (env NEXUS_CACERT)
  --resolve IP      connect to this IP but keep the URL host name (env
                    NEXUS_RESOLVE)
  -y, --yes         do not ask for confirmation
```

### nexusctl account delete

```text
usage: nexusctl account delete [-h] [--env-file FILE] [--url URL] [--user NAME]
                               [--insecure] [--cacert FILE] [--resolve IP] [-y]
                               [username]

positional arguments:
  username

options:
  -h, --help       show this help message and exit

connection and behaviour:
  --env-file FILE  read settings from this file (default ./.env and
                   ~/.config/nexusctl/env)
  --url URL        Nexus URL (env NEXUS_URL)
  --user NAME      Nexus admin user (env NEXUS_ADMIN_USER, default admin)
  --insecure       do not verify the TLS certificate (env NEXUS_INSECURE=1)
  --cacert FILE    CA file to trust (env NEXUS_CACERT)
  --resolve IP     connect to this IP but keep the URL host name (env
                   NEXUS_RESOLVE)
  -y, --yes        do not ask for confirmation
```
