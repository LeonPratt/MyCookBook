"""Local bearer authentication for every HTTP request, before MCP dispatch."""

from secrets import compare_digest

from starlette.datastructures import Headers
from starlette.responses import JSONResponse


class BearerAuth:
    def __init__(self, app, token):
        self.app = app
        self.token = token.encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            authorizations = headers.getlist("authorization")
            scheme, _, credential = (authorizations[0] if len(authorizations) == 1 else "").partition(" ")
            if scheme.lower() != "bearer" or not compare_digest(credential.encode("utf-8"), self.token):
                response = JSONResponse(
                    {"success": False, "error": {"code": "unauthorized", "message": "Supply a valid Bearer token."}},
                    status_code=401, headers={"WWW-Authenticate": 'Bearer realm="mycookbook-mcp"'},
                )
                await response(scope, receive, send)
                return
            if headers.get("sec-fetch-site", "").lower() in {"cross-site", "same-site"}:
                await JSONResponse({"error": "Cross-origin requests are not allowed"}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)
