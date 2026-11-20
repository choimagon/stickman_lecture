#!/usr/bin/env python3
"""Install the repository skill for Codex on Windows, macOS, or Linux."""

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "skills" / "stickman-lecture"
MARKER = ".runtime-root"


def install_copy(destination: Path) -> None:
    """Replace only a copy previously installed from this repository."""
    if destination.exists():
        marker = destination / MARKER
        try:
            managed_root = Path(marker.read_text(encoding="utf-8").strip()).resolve()
        except (OSError, ValueError):
            raise FileExistsError(f"A skill already exists at {destination}") from None
        if managed_root != ROOT:
            raise FileExistsError(f"A skill already exists at {destination}")

    with tempfile.TemporaryDirectory(prefix=".stickman-lecture-", dir=destination.parent) as temp:
        staging = Path(temp) / "skill"
        backup = Path(temp) / "backup"
        shutil.copytree(SOURCE, staging)
        (staging / MARKER).write_text(str(ROOT) + "\n", encoding="utf-8")
        had_previous = destination.exists()
        if had_previous:
            destination.rename(backup)
        try:
            staging.rename(destination)
        except OSError:
            if had_previous:
                backup.rename(destination)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, help="skills directory (default: CODEX_HOME/skills or ~/.codex/skills)")
    args = parser.parse_args()
    skill_dir = args.skill_dir or Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "skills"
    destination = skill_dir.expanduser() / "stickman-lecture"
    try:
        skill_dir.expanduser().mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            if destination.resolve() == SOURCE.resolve():
                print(f"StickMan Lecture is already linked at {destination}")
                return 0
            raise FileExistsError(f"A skill already exists at {destination}")
        if destination.exists():
            if sys.platform != "win32":
                raise FileExistsError(f"A skill already exists at {destination}")
            install_copy(destination)
            print(f"StickMan Lecture copy updated at {destination}")
            return 0
        try:
            destination.symlink_to(SOURCE, target_is_directory=True)
            print(f"StickMan Lecture linked at {destination}")
        except OSError:
            if sys.platform != "win32" or destination.exists() or destination.is_symlink():
                raise
            install_copy(destination)
            print(f"StickMan Lecture copied to {destination}. Run this installer again after skill updates.")
        return 0
    except OSError as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
