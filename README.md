# Ignition CI/CD

This repository is the infrastructure and configuration source for a new Ignition 8.3 development Gateway. It keeps Gateway configuration and Ignition projects on the host, alongside Docker deployment files, so changes can be reviewed and promoted through Git.

## Project structure

```text
.
├── docker-compose.yml
├── dockerfile.ignGit
├── README.md
├── scripts/
│   └── prepare-ignition-mounts.sh
├── provisioning/
│   └── ignition-entrypoint.sh
└── services/
    └── ignition/
        ├── config/
        │   └── resources/
        └── projects/
```

- `services/ignition/config/` is the host copy of Ignition's `data/config` directory.
- Keep `services/ignition/config/resources/` present. Ignition creates `.resources/` there at runtime; `.resources/` is excluded from Git.
- `services/ignition/projects/` contains one directory per Ignition project.
- Projects are normal directories in the infrastructure repository. Do not create nested Git repositories inside them.
- This is a new development deployment: no Gateway configuration or project was migrated into this workspace. Add project directories under `services/ignition/projects/` as they are created.

## Gateway and bind mounts

The Compose service builds the custom image from `inductiveautomation/ignition:8.3.10`. The Gateway runs as the `ignition` user configured by the image and retains the project-specific settings in [docker-compose.yml](./docker-compose.yml):

| Host path | Container path |
| --- | --- |
| `./services/ignition/config` | `/usr/local/bin/ignition/data/config` |
| `./services/ignition/projects` | `/usr/local/bin/ignition/data/projects` |

Both bind mounts are read/write. The service publishes Gateway HTTP on host port `5088` and HTTPS on `5043` (container ports `8088` and `8043`), uses the `ot-network-cicd` Compose network, and is configured with `restart: no`.

There is **no named volume** in the current Compose configuration. The mounted configuration and projects persist on the host and are versioned here. Other data under `/usr/local/bin/ignition/data` lives in the container's writable layer; it can be lost when the container is removed or recreated. Back up any runtime data that matters before replacing the container.

## First deployment

Run these steps from the repository root on the Docker host. The permission helper must be run from Bash (Git Bash or WSL on Windows):

```bash
docker compose config --quiet
docker compose build gateway
bash ./scripts/prepare-ignition-mounts.sh
docker compose up -d
```

The helper refuses to run while the Gateway is active. A temporary root helper creates `config/resources/.resources` and attempts to set group-write permissions for the image's `ignition` group without changing file owners. A second temporary helper tests file creation as `ignition`. It does not start the Gateway service. On Windows, Linux group/mode changes may not map to NTFS ACLs; if the write probe fails, grant the required access through the Docker Desktop/host ACL configuration and rerun the helper.

Check startup and access:

```powershell
docker compose ps
docker compose logs --tail 200 gateway
docker compose exec gateway id
docker inspect DEV_IgnitionSTD83_CICD --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
docker compose exec gateway sh -c 'ls -la /usr/local/bin/ignition/data/config /usr/local/bin/ignition/data/config/resources /usr/local/bin/ignition/data/projects'
```

Open `http://localhost:5088` or `https://localhost:5043` from the Docker host. Verify Gateway startup, configuration, and project loading in the Gateway interface/Designer. Static file checks alone do not validate Gateway runtime behavior.

## Day-to-day operation

```powershell
docker compose ps
docker compose logs -f gateway
docker compose stop gateway
docker compose start gateway
```

`docker compose stop` keeps the container and its writable layer. `docker compose down` removes the container; because the current Compose file has no named volume, data outside the two bind mounts will not survive that removal. Do not use `down` or force-recreate the Gateway without first backing up any needed runtime data.

The permission helper is for initial setup or permission repair while the Gateway is stopped; it is not part of every deployment. For subsequent changes to mounted configuration or projects, use the filesystem scans described below.

## Git and GitOps deployment flow

Use the infrastructure repository root for all Git operations. The development branch in this workspace is `dev`; use the deployment branch agreed by the team:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c feature/describe-change
# Edit configuration or project resources
git status
git diff
git add docker-compose.yml dockerfile.ignGit README.md .gitignore scripts provisioning services/ignition/config services/ignition/projects
git diff --cached
git commit -m "Describe the Ignition change"
git push -u origin feature/describe-change
```

Open a pull request, review the diff, and merge only after approval and secret checks. For an existing local branch without an upstream, configure it once with `git branch --set-upstream-to=origin/dev dev`.

The intended CI/CD flow is:

1. A pull request validates the Compose configuration and reviews the changed Gateway/project resources.
2. A protected merge to the deployment branch triggers a secured runner on the Docker host (or another runner with deliberate access to that host).
3. The runner fetches the approved revision and runs `docker compose config --quiet`.
4. For Compose or image changes, build and deploy with `docker compose up -d --build`, accounting for the container-layer data warning above.
5. For configuration/project-only changes, the runner updates the host checkout and triggers the relevant Gateway filesystem scan. Do not restart the container solely to make mounted file changes visible.

No CI workflow is included yet; this section describes the deployment contract for a future pipeline. Secure the runner, restrict deployment to protected branches/environments, and keep API credentials in the CI secret store—not in Git or command output. Do not expose a privileged Docker socket to untrusted pull-request jobs.

### Applying and scanning changes

After an approved checkout update, scan configuration under **Platform > System > Modes** and projects under **Platform > System > Projects** when required. The authenticated Gateway API also exposes `/data/api/v1/scan/config` and `/data/api/v1/scan/projects`. Use the Gateway's supported authentication and keep credentials in a secret store. Verify the result in the Gateway or Designer.

## Backup and rollback

- Git provides history for the committed host configuration and project resources; it does not back up secrets or container-layer runtime data.
- Create and retain Gateway backups and separate backups of any runtime data needed for recovery before recreating or removing the container.
- Roll back reviewed configuration through a revert commit and redeploy/scan that revision. Avoid destructive history rewrites.
- If a deployment fails, inspect `docker compose logs gateway`, restore the last known-good Git revision, and scan the restored files. Recreating the container does not restore unmounted runtime data.

## Security

- Do not commit passwords, tokens, private keys, keystores, local environment files, or unreviewed Gateway exports. `.gitignore` excludes common secret file types and environment-specific paths, but it does not replace review or secret scanning.
- Certificate and keystore directories are ignored. Provision required secrets securely outside Git and document their installation without recording secret values.
- The Compose command enables `ignition.allowunsignedmodules=true`. Keep it only where necessary and load only trusted modules; review this setting before production use.
- Keep development, staging, and production endpoints and credentials separate.

## Multiple Gateways

For future expansion, place each Gateway's `config/` and `projects/` under a distinct service directory, such as `services/gateway-01/` and `services/gateway-02/`. Use separate Compose services and deployment-specific settings. Share project directories only when their lifecycle and content are intentionally common across those Gateways.

## References

- [Ignition 8.3 Version and Source Control Guide](https://www.docs.inductiveautomation.com/docs/8.3/tutorials/version-control-guide)
- [Ignition 8.3 Gateway Folder Structure](https://www.docs.inductiveautomation.com/docs/8.3/appendix/reference-pages/gateway-folder-structure)
- [Official Ignition Docker image](https://hub.docker.com/r/inductiveautomation/ignition)
