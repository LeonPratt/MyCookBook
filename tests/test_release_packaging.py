import hashlib
import io
import tarfile

import pytest

from scripts import package_release, stage_pi_release


def test_package_contains_built_app_but_not_runtime_secrets(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    for name in [
        "wsgi.py",
        "requirements-prod.txt",
        "frontend/dist/index.html",
        "cookbook/__init__.py",
        ".env",
        "instance/cookbook.db",
        "frontend/node_modules/secret.js",
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("audit-only")
    monkeypatch.setattr(package_release, "ROOT", root)
    destination = tmp_path / "release.tar.gz"
    package_release.package_release(destination)
    with tarfile.open(destination) as archive:
        names = archive.getnames()
    assert "frontend/dist/index.html" in names
    assert "cookbook/__init__.py" in names
    assert not any(
        name.startswith((".env", "instance/", "frontend/node_modules/"))
        for name in names
    )
    with pytest.raises(ValueError, match="never overwritten"):
        package_release.package_release(destination)


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute/path", "linked"])
def test_stage_rejects_unsafe_archive_before_creating_release(tmp_path, unsafe):
    base = tmp_path / "app"
    base.mkdir()
    (base / ".mycookbook-deployment").write_text("MyCookBook deployment v1")
    archive_path = tmp_path / "bad.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo(unsafe)
        if unsafe == "linked":
            member.type = tarfile.SYMTYPE
            member.linkname = "../../escape"
            archive.addfile(member)
        else:
            member.size = 4
            archive.addfile(member, io.BytesIO(b"test"))
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Unsafe release"):
        stage_pi_release.stage(archive_path, base, "test-release", digest)
    assert not (base / "releases").exists()
    assert not (tmp_path / "escape").exists()


def test_stage_requires_verified_application_root(tmp_path):
    with pytest.raises(ValueError, match="inspected and initialized"):
        stage_pi_release.stage(tmp_path / "absent.tar.gz", tmp_path, "test", "bad")
