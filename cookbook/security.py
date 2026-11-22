"""Browser request boundaries for the trusted-LAN deployment."""

from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from flask import abort, request

LAN_NETWORKS = tuple(
    ip_network(value)
    for value in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "127.0.0.0/8",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def origin(value, *, referer=False):
    """Compare scheme, complete hostname and effective port, never prefixes."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if not referer and (parsed.path or parsed.query or parsed.fragment):
            return None
        port = (
            parsed.port
            if parsed.port is not None
            else (443 if parsed.scheme == "https" else 80)
        )
        return parsed.scheme, parsed.hostname.lower(), port
    except ValueError:
        return None


def register_security(app):
    allowed_hosts = {
        h.strip().lower().rstrip(".")
        for h in app.config["COOKBOOK_ALLOWED_HOSTS"]
        if h.strip()
    }

    @app.before_request
    def protect_requests():
        target = origin(request.host_url, referer=True)
        if target is None:
            abort(400, "Invalid request host")
        hostname = target[1].rstrip(".")
        trusted = hostname == "localhost" or hostname in allowed_hosts
        if not trusted:
            try:
                address = ip_address(hostname)
                trusted = any(
                    address.version == network.version and address in network
                    for network in LAN_NETWORKS
                )
            except ValueError:
                pass
        if not trusted:
            abort(
                400,
                "Untrusted request host. Use the server's LAN IP or a configured hostname.",
            )

        if not (request.path == "/api" or request.path.startswith("/api/")):
            return
        supplied_origin = request.headers.get("Origin")
        if supplied_origin is not None and origin(supplied_origin) != target:
            abort(403, "Cross-origin API requests are not allowed")
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        site = request.headers.get("Sec-Fetch-Site", "").lower()
        if site in ("cross-site", "same-site"):
            abort(403, "Cross-origin API requests are not allowed")
        # Browsers send Origin on writes. Referer is a fallback for older clients.
        # Headerless command-line clients remain supported; this is not authentication.
        if supplied_origin is None and "Referer" in request.headers:
            if origin(request.headers["Referer"], referer=True) != target:
                abort(403, "Cross-origin API requests are not allowed")

    @app.after_request
    def protect_framing(response):
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
