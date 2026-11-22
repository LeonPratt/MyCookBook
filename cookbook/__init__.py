import os
from pathlib import Path
import click
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_migrate import Migrate
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from .models import db


def create_app(config=None):
    load_dotenv()
    data_dir = Path(os.getenv("COOKBOOK_DATA_DIR", "instance")).resolve()
    app = Flask(__name__, instance_path=str(data_dir), static_folder=None)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "COOKBOOK_DATABASE_URL", "sqlite:///cookbook.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("COOKBOOK_MAX_UPLOAD_MB", "8")) * 1024 * 1024,
        UPLOAD_FOLDER=str(data_dir / "uploads"),
        COOKBOOK_ALLOWED_HOSTS=os.getenv("COOKBOOK_ALLOWED_HOSTS", "").split(","),
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    Migrate(app, db)
    from .routes import api

    app.register_blueprint(api, url_prefix="/api")
    from .security import register_security

    register_security(app)

    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify(
            error="Validation failed",
            details=[
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                for e in error.errors()
            ],
        ), 422

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        app.logger.exception("Request failed")
        return jsonify(error="An unexpected error occurred. Check the server log."), 500

    @app.get("/uploads/<path:name>")
    def upload(name):
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path=""):
        from flask import abort

        if path.startswith("api/") or path == "api":
            abort(404)
        root = Path(__file__).resolve().parent.parent / "frontend" / "dist"
        target = (root / path).resolve()
        if target.is_relative_to(root) and target.is_file():
            return send_from_directory(root, path)
        if (root / "index.html").is_file():
            return send_from_directory(root, "index.html")
        return (
            "Frontend not built. Run npm install and npm run build in frontend/.",
            503,
        )

    @app.cli.command("demo")
    @click.option("--remove", is_flag=True, help="Remove only bundled demo recipes.")
    def demo(remove):
        from .demo import seed

        click.echo(seed(remove))

    return app
