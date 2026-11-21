#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd "$repo_root"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI is required (run this from Git Bash or WSL with Docker access)." >&2
    exit 1
fi

docker compose config --quiet

running_container="$(docker compose ps --status running --quiet gateway)"
if [[ -n "$running_container" ]]; then
    echo "Stop the Gateway before preparing its bind mounts." >&2
    exit 1
fi

docker compose run --rm --no-deps -T --user 0:0 --entrypoint /bin/sh gateway -eu -c '
    config=/usr/local/bin/ignition/data/config
    projects=/usr/local/bin/ignition/data/projects
    resources="$config/resources"
    internal_resources="$resources/.resources"
    ignition_gid="$(id -g ignition)"

    mkdir -p "$resources" "$internal_resources" "$projects"

    if chgrp -R "$ignition_gid" "$config" "$projects" \
        && chmod -R g+rwX "$config" "$projects" \
        && find "$config" "$projects" -type d -exec chmod g+s {} +; then
        echo "Mounted paths assigned to Ignition group $ignition_gid with group write access."
    else
        echo "Could not apply Linux group/mode changes; checking effective bind-mount access." >&2
    fi
'

docker compose run --rm --no-deps -T --user ignition --entrypoint /bin/sh gateway -eu -c '
    for directory in \
        /usr/local/bin/ignition/data/config \
        /usr/local/bin/ignition/data/config/resources/.resources \
        /usr/local/bin/ignition/data/projects
    do
        if [ ! -d "$directory" ] || [ ! -w "$directory" ]; then
            echo "Ignition cannot write to $directory" >&2
            exit 1
        fi

        probe="$(mktemp "$directory/.ignition-write-test.XXXXXX")"
        rm -f "$probe"
    done
    echo "Ignition write checks passed for config, resources, and projects."
'
