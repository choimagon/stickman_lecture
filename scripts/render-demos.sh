#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$project_dir"
stickman-lecture render examples/mlp/scene.json --mode both
stickman-lecture render examples/kalman-filter/scene.json --mode video
stickman-lecture render examples/linear-algebra/scene.json --mode web
stickman-lecture render examples/rfs-intuition/scene.json --mode both
stickman-lecture render examples/shapes/scene.json --mode both
