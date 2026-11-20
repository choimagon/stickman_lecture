#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$project_dir"
mathscene render examples/mlp/scene.json --mode both
mathscene render examples/kalman-filter/scene.json --mode video
mathscene render examples/linear-algebra/scene.json --mode web
mathscene render examples/rfs-intuition/scene.json --mode both
