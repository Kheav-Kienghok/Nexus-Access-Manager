# Policies

A policy is one kind of access to the images of one project. Every account gets one or more policies on a project. Policies are cumulative: `pull,push` allows both.

| Policy | Allows | Nexus repository | Nexus actions |
|--------|--------|------------------|---------------|
| `read` | view images in the Nexus UI and search | `docker-all`, `docker-hosted` | `BROWSE` |
| `pull` | `docker pull` | `docker-all` | `BROWSE`, `READ` |
| `push` | `docker push`, including overwriting a tag such as `latest` | `docker-hosted` | `BROWSE`, `READ`, `ADD`, `EDIT` |
| `update` | modify or overwrite existing tags in the UI or API | `docker-hosted` | `BROWSE`, `READ`, `EDIT` |
| `delete` | delete tags and layers | `docker-hosted` | `BROWSE`, `READ`, `DELETE` |

Why `push` includes `EDIT`: pushing to a tag that already exists, which CI does for `latest`, is an edit in Nexus. Without `EDIT` the second push of the same tag is denied.

## Defaults

| Account | Default policies |
|---------|------------------|
| robot | `pull,push` |
| user | `read,pull,push,update,delete` (full access to the project) |

Both can be changed when they are created (`--policy`) and later (`nexusctl account policy`).

## Python mirror (pip)

Every account also gets the role `nexusctl-pip-pull`: `browse` and `read` on the Python repository (`pypi-all` by default, set `NEXUS_PYPI_REPO` to change it). It is read-only and not tied to a project. Leave it out with `--no-pip`, or switch it later with `nexusctl account pip USER on|off`.

`pypi-all` serves the PyPI cache and your internal Python packages. Set `NEXUS_PYPI_REPO=pypi-proxy` before creating accounts if they should only see the public cache.

## What exists in Nexus for a project

For a project `speedtest`, `nexusctl project create speedtest` creates 12 objects:

| Kind | Names |
|------|-------|
| content selector | `proj-speedtest` with the expression `format == "docker" and path =^ "/v2/speedtest/"` |
| privileges | `proj-speedtest-read-all`, `proj-speedtest-read-hosted`, `proj-speedtest-pull-all`, `proj-speedtest-push-hosted`, `proj-speedtest-update-hosted`, `proj-speedtest-delete-hosted` |
| roles | `proj-speedtest-read`, `proj-speedtest-pull`, `proj-speedtest-push`, `proj-speedtest-update`, `proj-speedtest-delete` |

An account's policies are simply the `proj-<project>-<policy>` roles it holds. Running the command again keeps what exists and refreshes the roles.
