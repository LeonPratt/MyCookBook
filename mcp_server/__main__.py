"""Run from the repository root: python -m mcp_server."""

import logging

import uvicorn

from .config import Config
from .server import create_http_app


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    try:
        config = Config.from_env()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    uvicorn.run(create_http_app(config), host=config.host, port=config.port,
                workers=1, proxy_headers=False, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
