# Ignition CI/CD

This repository is the infrastructure and configuration source for a new Ignition 8.3 development Gateway. It keeps Gateway configuration and Ignition projects on the host, alongside Docker deployment files, so changes can be reviewed and promoted through Git.

## Project structure

```text
.
├── docker-compose.yml
├── dockerfile.ignGit
├── README.md
├── .env.example
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

## Environment variables

Compose injects the Gateway's environment from the root `.env` file through the service's `env_file` setting. The current values are:

| Variable | Purpose |
| --- | --- |
| `ACCEPT_IGNITION_EULA` | Accepts the Inductive Automation software license terms when set to `Y`. |
| `IGNITION_EDITION` | Selects the Gateway edition; currently `standard`. |
| `TZ` | Sets the container timezone; currently `America/Mexico_City`. |

The local `.env` is ignored by Git. `.env.example` is the versioned template for a fresh clone and for future additions. Before first deployment, create the local file without overwriting an existing one:

```bash
test -f .env || cp .env.example .env
```

When adding an image-specific variable, first check the [official Ignition Docker Image documentation](https://docs.inductiveautomation.com/docs/8.3/platform/docker-image). Add the variable to `.env.example` with a safe, non-secret development value, add the required value to the Docker host's untracked `.env`, and keep `env_file` in Compose. Do not put credentials or production secrets in the template or repository; materialize those from the CI/CD secret store on the deployment host.

Environment changes take effect when the container is recreated. Before recreating it with `docker compose up -d --force-recreate gateway`, back up any required runtime data outside the bind mounts.

## First deployment

Run these steps from the repository root on the Docker host. The permission helper must be run from Bash (Git Bash or WSL on Windows):

```bash
test -f .env || cp .env.example .env
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
git add docker-compose.yml dockerfile.ignGit README.md .gitignore .env.example scripts provisioning services/ignition/config services/ignition/projects
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

# SSH Authentication with GitHub on Ubuntu

Guide to configure SSH authentication using a GitHub Deploy Key on an Ubuntu server.

## 1. Install Git and SSH Client

```bash
sudo apt update
sudo apt install git openssh-client -y
```

## 2. Generate an SSH Key Pair

Create the SSH directory if it doesn't exist:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

Generate an Ed25519 key dedicated to the Ignition repository:

```bash
ssh-keygen -t ed25519 \
  -C "ignition-infrastructure" \
  -f ~/.ssh/ignition_github
```

Set a passphrase when prompted.

Set the appropriate permissions:

```bash
chmod 600 ~/.ssh/ignition_github
chmod 644 ~/.ssh/ignition_github.pub
```

The generated files are:

- `~/.ssh/ignition_github`: Private key. Never share or commit it.
- `~/.ssh/ignition_github.pub`: Public key. This is the key shared with GitHub.

## 3. Configure GitHub Deploy Key

Display the public key:

```bash
cat ~/.ssh/ignition_github.pub
```

Copy its contents and navigate to:

GitHub Repository → Settings → Deploy keys → Add deploy key.

Configure:

- Title: `Ubuntu Ignition Development Server`
- Key: Paste the public key.
- Enable: **Allow write access**.

Save the Deploy Key.

## 4. Configure SSH Client

Create or edit:

```bash
nano ~/.ssh/config
```

Add:

```sshconfig
Host github-ignition
    HostName github.com
    User git
    IdentityFile ~/.ssh/ignition_github
    IdentitiesOnly yes
```

Set permissions:

```bash
chmod 600 ~/.ssh/config
```

## 5. Configure Git Remote

For an existing repository:

```bash
git remote set-url origin \
git@github-ignition:USERNAME/REPOSITORY.git
```

Verify:

```bash
git remote -v
```

Test SSH authentication:

```bash
ssh -T git@github-ignition
```

Expected response:

```text
Hi USERNAME! You've successfully authenticated,
but GitHub does not provide shell access.
```

## 6. Start SSH Agent

Start the SSH agent:

```bash
eval "$(ssh-agent -s)"
```

Load the private key:

```bash
ssh-add ~/.ssh/ignition_github
```

Enter the passphrase when prompted.

Verify loaded identities:

```bash
ssh-add -l
```

The key is now available for Git operations without entering the passphrase again while the agent remains accessible.

## 7. Git Operations

You can now perform Git operations normally:

```bash
git status
git add .
git commit -m "Update Ignition configuration"
git push origin develop
```

No additional passphrase prompt should appear while the key remains loaded in the agent.

## 8. Remove SSH Key from Agent

If you want to unload the private key but keep the agent running:

```bash
ssh-add -d ~/.ssh/ignition_github
```

Alternatively, remove all loaded keys:

```bash
ssh-add -D
```

## 9. Stop SSH Agent

When finished, terminate the SSH agent:

```bash
ssh-agent -k
```

This terminates the agent and unloads its keys from memory.

Verify:

```bash
ssh-add -l
```

If the agent has terminated, the command may report that it cannot connect to the authentication agent.

## 10. Next SSH Session

When connecting to Ubuntu again, repeat:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/ignition_github
```

Enter the passphrase and continue working.

---

## Security Recommendations

- Never commit private SSH keys to Git.
- Never copy private keys into Docker images.
- Do not mount `~/.ssh` inside the Ignition container.
- Use a dedicated Deploy Key with write access only to the required repository.
- Keep appropriate filesystem permissions on `~/.ssh`.
- Protect the Ubuntu account with strong authentication.
- Unload SSH keys when finishing sensitive administrative sessions.

**Architecture:** Git and SSH authentication run on the Ubuntu host. The Ignition container only accesses configuration and project files through Docker bind mounts.

## References

- [Ignition 8.3 Version and Source Control Guide](https://www.docs.inductiveautomation.com/docs/8.3/tutorials/version-control-guide)
- [Ignition 8.3 Gateway Folder Structure](https://www.docs.inductiveautomation.com/docs/8.3/appendix/reference-pages/gateway-folder-structure)
- [Ignition Docker Image documentation — environment variables and runtime arguments](https://docs.inductiveautomation.com/docs/8.3/platform/docker-image)
- [Official Ignition Docker image](https://hub.docker.com/r/inductiveautomation/ignition)
