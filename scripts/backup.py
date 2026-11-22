"""Online SQLite snapshot + uploaded photos. Run from the repository root."""

import argparse
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from cookbook import create_app
from cookbook.models import db


def backup(destination):
    app = create_app()
    with app.app_context():
        if db.engine.dialect.name != "sqlite":
            raise ValueError("This backup utility supports SQLite only")
        target = Path(destination).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "cookbook.db"
            connection = db.engine.raw_connection()
            try:
                with closing(sqlite3.connect(snapshot)) as dest:
                    connection.driver_connection.backup(dest)
            finally:
                connection.close()
                db.engine.dispose()
            with zipfile.ZipFile(
                target, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.write(snapshot, "cookbook.db")
                for image in Path(app.config["UPLOAD_FOLDER"]).glob("*"):
                    if image.is_file():
                        archive.write(image, "uploads/" + image.name)
        print(target)
        return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination",
        nargs="?",
        default="backups/mycookbook-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + ".zip",
    )
    backup(parser.parse_args().destination)
