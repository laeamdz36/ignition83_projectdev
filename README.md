# Ignition Infrastructure

This repository keeps the Ignition 8.3 Gateway configuration and project resources on the host so they can be reviewed and versioned together with the Docker deployment.

## Repository layout

```text
.
├── docker-compose.yml
├── dockerfile.ignGit
├── README.md
├── provisioning/
│   └── ignition-entrypoint.sh
└── services/
    └── ignition/
        ├── config/
        └── projects/
```

- `services/ignition/config/` contains the curated contents of Ignition's `data/config` directory.
- Keep `services/ignition/config/resources/` present. Ignition creates its runtime `.resources/` directory there; `.resources/` remains excluded from Git.
- `services/ignition/projects/` contains one directory per Ignition project.
- Keep each project as a normal directory in the root Git repository. Do not initialize Git repositories inside projects.
- `gw-datastd83` remains a Docker named volume for the rest of `data`, including runtime state. It is not the Git source of truth for the two bind-mounted directories.

### Initial migration status

The workspace initially contained no Gateway configuration or project resources. The directory placeholders do not represent a migrated Gateway or the `dfo_rcms` project. Add the actual resources from a verified Gateway export before relying on this repository as a backup.

## Docker mounts and image

The Compose service retains the existing custom build based on `inductiveautomation/ignition:8.3.10`, service settings, ports, environment, network, command, and named data volume. The bind mounts are:

| Host path | Container path |
| --- | --- |
| `./services/ignition/config` | `/usr/local/bin/ignition/data/config` |
| `./services/ignition/projects` | `/usr/local/bin/ignition/data/projects` |

The named volume is mounted at `/usr/local/bin/ignition/data` as well, preserving runtime data outside the curated child mounts. A bind mount overlays its target path; it does not delete the underlying volume contents, but those contents are hidden while the bind mount is active. Before the first start on any Docker host, verify that the existing `gw-datastd83` volume does not contain configuration or projects that have not been copied to the host.

The image is configured as user `ignition` in `dockerfile.ignGit`. The actual numeric UID/GID and host bind-mount access depend on the built image and Docker host and must be checked there. On Linux, grant only the needed read/write access to the verified container UID/GID. On Windows with Docker Desktop, check the directory ACL and verify access from the container; do not use `chmod 777`.

## Start, stop, and inspect

From the repository root:

```powershell
docker compose config
docker compose up -d
docker compose ps
docker compose logs -f gateway
docker compose stop gateway
```

`docker compose down` removes the container and network but normally leaves named volumes. Do not use `docker compose down -v` for routine operation: it removes named volumes and can destroy runtime data.

Check the user and mounted paths after starting:

```powershell
docker compose exec gateway id
docker inspect DEV_IgnitionSTD83 --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
docker compose exec gateway sh -c 'ls -la /usr/local/bin/ignition/data/config /usr/local/bin/ignition/data/projects'
```

Run these checks on the intended Docker host. Static validation of this repository does not validate Gateway runtime behavior.

## Updating and scanning resources

After changing Gateway configuration or project files:

1. Review the file changes and ensure no secrets or local-only values are included.
2. In the Gateway web interface, scan configuration under **Platform > System > Modes** and projects under **Platform > System > Projects**, when required.
3. Alternatively, use the authenticated Gateway API endpoints `/data/api/v1/scan/config` and `/data/api/v1/scan/projects`.
4. Verify the Gateway and projects in the web interface or Designer.

When retrieving changes from GitHub, review the branch and diff first, then scan the affected configuration or projects in the Gateway. File changes alone should not be treated as proof that the Gateway successfully loaded them.

## Git workflow

Use the infrastructure repository root for all Git operations:

```powershell
git status
git diff
git add docker-compose.yml dockerfile.ignGit README.md .gitignore services/ignition/config services/ignition/projects
git diff --cached
git commit -m "Describe the Ignition configuration change"
git branch -M main
git remote add origin <github-repository-url>
git push -u origin main
```

To retrieve approved changes:

```powershell
git switch main
git pull --ff-only origin main
```

This workspace currently has no configured `origin` remote and no commits on its active branch. Use the remote/branch setup commands only for the initial publication; never stage credential files, and review `git diff --cached` before every commit.

## Backup and rollback

- Before changing mounts or applying a large configuration update, create a Gateway backup and a separate backup of the complete named data volume.
- Keep the original volume intact until the mounted configuration and projects have been checked in the Gateway.
- If the Gateway fails after a mount change, stop it, revert the Compose change, and restart against the unchanged named volume. Do not delete the original volume or host files during rollback.
- A Gateway backup and a copy of the named volume serve different purposes; retain both according to the operational recovery policy.

## Security

- Do not commit passwords, tokens, private keys, keystores, local environment files, or unreviewed Gateway exports. `.gitignore` excludes common secret file types and environment-specific paths, but ignore rules are not a substitute for review or secret scanning.
- Certificate and keystore directories are ignored. If a Gateway needs them, provision them securely outside Git and document the process without recording secret values.
- The Compose command currently enables `ignition.allowunsignedmodules`. Retain that setting only where required and only with trusted modules; review it before using this deployment in a security-sensitive environment.
- Keep development, staging, and production credentials and endpoints separate. Do not use a development Gateway volume as a production backup.

## Multiple Gateways

For future expansion, place each Gateway's `config/` and `projects/` under a distinct service directory, for example `services/gateway-01/` and `services/gateway-02/`, and use separate named runtime volumes. Share project directories only when those projects are intentionally identical across Gateways and deployment changes are coordinated.

## References

- [Ignition 8.3 Version and Source Control Guide](https://www.docs.inductiveautomation.com/docs/8.3/tutorials/version-control-guide)
- [Ignition 8.3 Gateway Folder Structure](https://www.docs.inductiveautomation.com/docs/8.3/appendix/reference-pages/gateway-folder-structure)
