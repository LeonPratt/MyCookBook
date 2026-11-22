"""Restore an archive. Stop the application service first. Requires --replace."""

import argparse
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from cookbook import create_app
from cookbook.models import db


def restore(source, replace=False):
    if not replace:
        raise ValueError(
            "Restore replaces the database. Back up first, stop the service, then use --replace."
        )
    app = create_app()
    with app.app_context():
        if db.engine.dialect.name != "sqlite":
            raise ValueError("This restore utility supports SQLite only")
        target = Path(db.engine.url.database).resolve()
        upload = Path(app.config["UPLOAD_FOLDER"]).resolve()
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if names.count("cookbook.db") != 1 or len(names) != len(set(names)):
                raise ValueError(
                    "Archive must contain exactly one cookbook.db and no duplicate paths"
                )
            if any(
                name != "cookbook.db"
                and not re.fullmatch(r"uploads/[a-f0-9]{32}\.(jpg|png|webp)", name)
                for name in names
            ):
                raise ValueError("Archive contains an unexpected or unsafe path")
            if sum(i.file_size for i in archive.infolist()) > 5_000_000_000:
                raise ValueError("Archive exceeds the 5 GB restore limit")
            with tempfile.TemporaryDirectory(dir=target.parent) as directory:
                stage = Path(directory)
                for name in names:
                    output = stage / name
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as src, output.open("wb") as dest:
                        shutil.copyfileobj(src, dest)
                with closing(sqlite3.connect(stage / "cookbook.db")) as connection:
                    if (
                        connection.execute("PRAGMA integrity_check").fetchone()[0]
                        != "ok"
                    ):
                        raise ValueError("Backup database failed integrity validation")
                    tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }
                    if not {
                        "recipe",
                        "cooking_session",
                        "shopping_item",
                        "setting",
                        "alembic_version",
                    }.issubset(tables):
                        raise ValueError("Not a migrated MyCookBook database")
                db.session.remove()
                db.engine.dispose()
                # Retain a recoverable copy before changing either database or photos.
                recovery = target.with_suffix(".pre-restore.db")
                if target.exists():
                    if recovery.exists():
                        raise ValueError(
                            "A .pre-restore.db already exists. Move it aside before restoring again."
                        )
                    shutil.copy2(target, recovery)
                for image in (stage / "uploads").glob("*"):
                    shutil.copy2(image, upload / image.name)
                os.replace(stage / "cookbook.db", target)
        print(
            "Restored database and referenced photos. Run flask --app wsgi db upgrade before restarting."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    restore(args.archive, args.replace)
