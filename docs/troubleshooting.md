# Troubleshooting

Start with:

```bash
nexusctl check
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `error: set NEXUS_URL` | no URL configured | set `NEXUS_URL` in `.env` or pass `--url` |
| `error: set NEXUS_ADMIN_PASSWORD` | no admin password and no terminal to ask | set it in `.env` or the environment |
| `Nexus rejected the admin login (401)` | wrong admin user or password | check `NEXUS_ADMIN_USER` and `NEXUS_ADMIN_PASSWORD` |
| `cannot reach Nexus` | wrong URL, Nexus down, or not published (Nexus only listens inside the Podman network) | use the Caddy URL; on the Nexus VM add `NEXUS_RESOLVE=127.0.0.1` |
| `TLS failed` | the certificate is not trusted | `NEXUS_CACERT=/path/to/ca.crt`, or `NEXUS_INSECURE=1` for a local test |
| `check`: repository missing | `docker-all`, `docker-hosted` or the Python repository does not exist, or has another name | create them, or set `NEXUS_PULL_REPO`, `NEXUS_PUSH_REPO`, `NEXUS_PYPI_REPO` |
| `check`: Docker Bearer Token Realm not active | Docker clients cannot log in | Nexus UI: Settings > Security > Realms, add Docker Bearer Token Realm |
| `Nexus returned 400 ... privilege` when creating a project | the content selector privilege API rejected the request | check the Nexus version and the repository names in `check` |
| `docker push` denied with `push` policy | the image name does not start with `<project>/`, or the login is for another account | push to `host:5002/<project>/<image>:<tag>` and run `docker login` with the account |
| `docker pull` denied for a project image | account lacks `pull`, or anonymous access is off and nobody logged in | `nexusctl account show USER`, then `docker login` |
| pip `401` | the account was created with `--no-pip`, or the pip URL has no credentials | `nexusctl account pip USER on`, use `https://USER:PASSWORD@host/repository/pypi-all/simple` |
| `user X already exists` | the name is taken, maybe by a user created in the Nexus UI | pick another name, or change an existing account with `account policy` |
| `X was not created by nexusctl` | the target is not one of its accounts | manage it in the Nexus UI |

## Check the content selector

The selector expression uses the Docker path format `/v2/<project>/`. If images of a project cannot be pulled or pushed although the policies are right, preview the selector in the Nexus UI: Settings > Repository > Content Selectors > `proj-<project>` > preview against `docker-hosted` and `docker-all`. If the path format differs on your Nexus version, adjust the expression there.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```

The tests run the CLI against an in-memory fake of the Nexus API, including an HTTPS server for the `--resolve` and CA checks. They do not need a real Nexus.
