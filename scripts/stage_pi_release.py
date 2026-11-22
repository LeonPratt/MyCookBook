"""Stage a new, unprivileged Pi release; never switch/start services or touch data."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath


def stage(archive, base, release, checksum):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", release):
        raise ValueError("Invalid release identifier")
    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11 or newer is required")
    os.umask(0o077)
    base = Path(base).resolve()
    marker = base / ".mycookbook-deployment"
    if not marker.is_file() or marker.read_text().strip() != "MyCookBook deployment v1":
        raise ValueError("Deployment root must first be inspected and initialized")
    archive = Path(archive).resolve()
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError("Release archive checksum mismatch")
    target = base / "releases" / release
    if target.exists():
        raise ValueError("Release already exists; choose a new identifier")
    if shutil.disk_usage(base).free < 200 * 1024 * 1024:
        raise ValueError("At least 200 MiB free is required before staging a release")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if len(members) > 1000 or sum(m.size for m in members) > 100 * 1024 * 1024:
            raise ValueError("Unexpected release archive size")
        names = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or member.name in names
            ):
                raise ValueError("Unsafe release member")
            names.add(member.name)
        if not {
            "wsgi.py",
            "requirements-prod.txt",
            "frontend/dist/index.html",
        }.issubset(names):
            raise ValueError("Incomplete application bundle")
        target.mkdir(parents=True, exist_ok=False)
        for member in members:
            output = target / member.name
            output.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source, output.open("xb") as destination:
                shutil.copyfileobj(source, destination)
    subprocess.run([sys.executable, "-m", "venv", str(target / ".venv")], check=True)
    python = target / ".venv/bin/python"
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--only-binary=:all:",
            "-r",
            str(target / "requirements-prod.txt"),
        ],
        check=True,
    )
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    print(json.dumps({"staged_release": str(target), "python": str(python)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--base", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    stage(args.archive, args.base, args.release, args.sha256)
