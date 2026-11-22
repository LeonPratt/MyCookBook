"""Run management commands with a private deployment environment file."""

import argparse
import json
import os
from pathlib import Path

from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    sub.add_parser("check")
    sub.add_parser("serve")
    backup_parser = sub.add_parser("backup")
    backup_parser.add_argument("destination")
    args = parser.parse_args()
    env_file = Path(args.env_file)
    if not env_file.is_file():
        parser.error("Environment file is missing")
    os.environ.update(
        {
            key: value
            for key, value in dotenv_values(env_file, interpolate=False).items()
            if value is not None
        }
    )
    if args.command == "serve":
        from scripts.serve import main as serve

        serve()
    elif args.command == "backup":
        from scripts.backup import backup

        backup(args.destination)
    else:
        from cookbook import create_app
        from cookbook.models import db, Recipe, CookingSession, ShoppingItem

        app = create_app()
        with app.app_context():
            if args.command == "migrate":
                from flask_migrate import upgrade

                upgrade(
                    directory=str(Path(__file__).resolve().parent.parent / "migrations")
                )
            else:
                print(
                    json.dumps(
                        {
                            "recipes": db.session.query(Recipe).count(),
                            "history": db.session.query(CookingSession).count(),
                            "shopping_items": db.session.query(ShoppingItem).count(),
                        }
                    )
                )
            db.session.remove()
            db.engine.dispose()


if __name__ == "__main__":
    main()
