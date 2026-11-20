#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
skill_dir="${1:-${CODEX_HOME:-$HOME/.codex}/skills}"
destination="$skill_dir/mathscene"

mkdir -p -- "$skill_dir"
if [[ -L "$destination" && "$(readlink "$destination")" == "$project_dir/skills/mathscene" ]]; then
    printf 'MathScene is already linked at %s\n' "$destination"
    exit 0
fi
if [[ -e "$destination" || -L "$destination" ]]; then
    printf 'A skill already exists at %s\n' "$destination" >&2
    exit 1
fi
ln -s -- "$project_dir/skills/mathscene" "$destination"
printf 'MathScene linked at %s\n' "$destination"
