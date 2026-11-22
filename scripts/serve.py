"""Serve the built app with the platform's production WSGI server."""

import os
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()
    host = os.getenv("COOKBOOK_HOST", "127.0.0.1")
    port = int(os.getenv("COOKBOOK_PORT", "5432"))
    if sys.platform == "win32":
        from waitress import serve
        from cookbook import create_app

        display_host = "localhost" if host in ("0.0.0.0", "::") else host
        if ":" in display_host:
            display_host = f"[{display_host}]"
        print(f"MyCookBook: http://{display_host}:{port}", flush=True)
        serve(create_app(), host=host, port=port)
    else:
        from gunicorn.app.wsgiapp import run

        os.environ.setdefault("COOKBOOK_HOST", host)
        os.environ.setdefault("COOKBOOK_PORT", str(port))
        sys.argv = ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
        run()


if __name__ == "__main__":
    main()
