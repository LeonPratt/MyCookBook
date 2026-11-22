import io

import pytest
from PIL import Image, XbmImagePlugin


@pytest.mark.parametrize(
    "base",
    [
        "http://localhost",
        "http://localhost:5432",
        "http://127.0.0.1:5432",
        "http://192.168.0.251:5432",
        "http://10.0.0.5:5432",
        "http://[::1]:5432",
        "http://[fd00::1]:5432",
    ],
)
def test_local_and_lan_same_origin_writes_work(client, recipe, base):
    response = client.post(
        "/api/recipes",
        base_url=base,
        headers={"Origin": base, "Sec-Fetch-Site": "same-origin"},
        json=recipe,
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://attacker.example"},
        {"Origin": "http://localhost.attacker.example"},
        {"Origin": "http://localhost:5432"},
        {"Origin": "https://localhost"},
        {"Origin": "null"},
        {"Origin": "http://localhost/path"},
        {"Origin": "http://localhost#fragment"},
        {"Origin": "http://localhost:bad"},
        {"Origin": "http://localhost:0"},
        {"Origin": "http://user@localhost"},
        {"Origin": "http://localhost https://attacker.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Referer": "https://attacker.example/page"},
        {"Referer": "not a URL"},
    ],
)
def test_cross_origin_writes_rejected_without_database_changes(client, recipe, headers):
    response = client.post("/api/recipes", json=recipe, headers=headers)
    assert response.status_code == 403
    assert client.get("/api/recipes").json == []


def test_bodiless_form_posts_and_deletes_are_protected(client, recipe):
    recipe_id = client.post("/api/recipes", json=recipe).json["id"]
    headers = {"Origin": "https://attacker.example"}
    assert client.post("/api/demo", data={}, headers=headers).status_code == 403
    assert (
        client.post(
            f"/api/recipes/{recipe_id}/duplicate", data={}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/recipes/{recipe_id}", headers=headers).status_code == 403
    )
    assert len(client.get("/api/recipes").json) == 1


def test_origin_comparison_accepts_default_port_and_referer_path(client, recipe):
    assert (
        client.post(
            "/api/recipes", json=recipe, headers={"Origin": "http://LOCALHOST:80"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/recipes",
            json=recipe,
            headers={"Referer": "http://localhost/recipes?meal=1"},
        ).status_code
        == 201
    )
    # Vite retains the browser's Host header when proxying to Flask on port 5432.
    assert (
        client.post(
            "/api/recipes",
            base_url="http://localhost:5173",
            json=recipe,
            headers={"Origin": "http://localhost:5173"},
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "host",
    [
        "attacker.example",
        "localhost.attacker.example",
        "192.168.0.251.attacker.example",
        "8.8.8.8",
        "0.0.0.0",
    ],
)
def test_untrusted_hostnames_rejected_for_reads_and_writes(client, recipe, host):
    assert client.get("/api/settings", headers={"Host": host}).status_code == 400
    assert (
        client.post("/api/recipes", json=recipe, headers={"Host": host}).status_code
        == 400
    )


def test_explicit_custom_hostname_is_allowed(app, recipe):
    from cookbook import create_app

    custom = create_app(
        {
            **{k: app.config[k] for k in ["SQLALCHEMY_DATABASE_URI", "UPLOAD_FOLDER"]},
            "TESTING": True,
            "COOKBOOK_ALLOWED_HOSTS": ["cookbook.local"],
        }
    )
    response = custom.test_client().post(
        "/api/recipes",
        base_url="http://cookbook.local:5432",
        headers={"Origin": "http://cookbook.local:5432"},
        json=recipe,
    )
    assert response.status_code == 201


def test_cross_origin_upload_cannot_write_files(client, app):
    image = io.BytesIO()
    Image.new("RGB", (1, 1)).save(image, "PNG")
    image.seek(0)
    response = client.post(
        "/api/images",
        headers={"Origin": "https://attacker.example"},
        data={"image": (image, "image.png")},
    )
    assert response.status_code == 403
    from pathlib import Path

    assert list(Path(app.config["UPLOAD_FOLDER"]).iterdir()) == []


def test_disallowed_image_decoder_is_never_invoked(client, monkeypatch):
    calls = []

    def forbidden(image):
        calls.append(True)
        raise AssertionError("Unsupported XBM decoder was invoked")

    monkeypatch.setattr(XbmImagePlugin.XbmImageFile, "_open", forbidden)
    benign = b"#define im_width 1\n#define im_height 1\nstatic unsigned char im_bits[] = { 0x00 };\n"
    response = client.post(
        "/api/images", data={"image": (io.BytesIO(benign), "photo.jpg")}
    )
    assert response.status_code == 422
    assert calls == []


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_supported_uploads_still_work(client, format):
    image = io.BytesIO()
    Image.new("RGB", (10, 10)).save(image, format)
    image.seek(0)
    response = client.post(
        "/api/images",
        headers={"Origin": "http://localhost"},
        data={"image": (image, "photo." + format.lower())},
    )
    assert response.status_code == 201
    assert client.get(response.json["image_path"]).status_code == 200


def test_preflight_and_framing_headers(client):
    assert (
        client.options(
            "/api/recipes",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        ).status_code
        == 403
    )
    response = client.get("/api/settings")
    assert response.headers.get("Access-Control-Allow-Origin") is None
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'self'"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_cross_origin_llm_request_cannot_reach_provider(client, monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Cross-origin request reached LLM provider")

    monkeypatch.setattr("cookbook.routes.urllib.request.urlopen", forbidden)
    response = client.post(
        "/api/import/text",
        json={"text": "Synthetic recipe", "use_llm": True},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert calls == []
