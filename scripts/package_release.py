"""Package a locally built frontend and an explicit server-source allowlist."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILES = [
    "wsgi.py",
    "gunicorn.conf.py",
    "requirements-prod.txt",
    "requirements.txt",
    "README.md",
    "DEPLOYMENT.md",
    "AGENTS.md",
]
SOURCE_DIRS = ["cookbook", "migrations", "scripts", "deploy", "docs"]


def package_release(destination):
    destination = Path(destination).resolve()
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise ValueError("Build frontend/ with npm run build first")
    if destination.exists():
        raise ValueError(
            "Choose a new archive path; existing archives are never overwritten"
        )
    paths = [ROOT / name for name in SOURCE_FILES if (ROOT / name).is_file()]
    for directory in SOURCE_DIRS + ["frontend/dist"]:
        paths.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        for path in sorted(set(paths)):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in source package: {path}")
            archive.add(
                path, arcname=path.relative_to(ROOT).as_posix(), recursive=False
            )
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = {
        "archive": destination.name,
        "sha256": checksum,
        "files": sorted(p.relative_to(ROOT).as_posix() for p in set(paths)),
    }
    destination.with_suffix(destination.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"archive": str(destination), "sha256": checksum, "files": len(paths)}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    package_release(parser.parse_args().destination)
