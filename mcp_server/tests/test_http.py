import asyncio
import socket
import threading
import time

import pytest

pytest.importorskip("mcp")

import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from mcp_server.config import Config
from mcp_server.server import create_http_app


def rpc(client, name, arguments=None, headers=None):
    return client.post("/mcp", headers={"Accept": "application/json, text/event-stream", **(headers or {})},
                       json={"jsonrpc": "2.0", "id": 1, "method": name, "params": arguments or {}})


@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Basic wrong", "", "Bearer "])
def test_authentication_required_before_dispatch(app, config, recipe, authorization):
    with TestClient(create_http_app(config, app), base_url="http://localhost:8001") as client:
        headers = {} if authorization is None else {"Authorization": authorization}
        response = rpc(client, "tools/call", {"name": "add_recipe", "arguments": {"recipe": recipe}}, headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.headers["www-authenticate"].startswith("Bearer")
        assert client.get("/mcp", headers=headers).status_code == 401
        assert client.delete("/mcp", headers=headers).status_code == 401
    assert app.test_client().get("/api/recipes").json == []


def test_protocol_security_and_limits(app, config, recipe):
    with TestClient(create_http_app(config, app), base_url="http://localhost:8001",
                    headers={"Authorization": f"Bearer {config.token}"}) as client:
        initialized = rpc(client, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
        assert initialized.status_code == 200 and "result" in initialized.json()
        tools = rpc(client, "tools/list").json()["result"]["tools"]
        assert len(tools) == 7
        assert rpc(client, "tools/list", headers={"Host": "evil.invalid"}).status_code == 421
        assert rpc(client, "tools/list", headers={"Origin": "https://foreign.invalid"}).status_code == 403
        assert rpc(client, "tools/list", headers={"Origin": "null"}).status_code == 403
        assert rpc(client, "tools/list", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        assert client.post("/mcp", content=b"x" * (2 * 1024 * 1024 + 1), headers={"Content-Type": "application/json"}).status_code == 413
        created = rpc(client, "tools/call", {"name": "add_recipe", "arguments": {"recipe": recipe}}).json()["result"]
        assert created["structuredContent"]["success"]
        assert config.token not in str(created)
        invalid = rpc(client, "tools/call", {"name": "add_recipe", "arguments": {"recipe": {}}}).json()["result"]
        assert invalid["isError"] and invalid["structuredContent"]["error"]["code"] == "validation_error"


def test_official_client_over_real_streamable_http(app, recipe):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    config = Config(token="x" * 48, port=listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(create_http_app(config, app), host=config.host,
                                         port=config.port, log_level="critical", access_log=False, proxy_headers=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started
        async def exercise():
            async with httpx.AsyncClient(headers={"Authorization": f"Bearer {config.token}"}) as http:
                async with streamable_http_client(f"http://127.0.0.1:{config.port}/mcp", http_client=http) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        assert len((await session.list_tools()).tools) == 7
                        saved = await session.call_tool("add_recipe", {"recipe": recipe})
                        assert not saved.isError
                        row = await session.call_tool("get_recipe", {"recipe_id": saved.structuredContent["recipe_id"]})
                        assert row.structuredContent["recipe"]["ingredients"][0]["quantity"] == 300
        asyncio.run(exercise())
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
    assert not thread.is_alive()


def test_config_fails_closed_and_hides_secret():
    for args in [{"token": ""}, {"token": "short"}, {"token": "x" * 32, "host": "0.0.0.0"},
                 {"token": "x" * 32, "allowed_hosts": ("*",)},
                 {"token": "x" * 32, "recipe_base_url": "https://user:password@example.com"}]:
        with pytest.raises(ValueError):
            Config(**args)
    secret = "sensitive-token-" + "x" * 32
    assert secret not in repr(Config(token=secret))
