import json
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

import pytest

import main


def test_launcher_serves_dashboard_when_default_port_is_taken(tmp_path, monkeypatch):
    import launcher

    monkeypatch.setattr(main, "ROOT", tmp_path)
    occupied = ThreadingHTTPServer(("127.0.0.1", 0), main.handler_for(main.LabService()))
    session = launcher.LauncherSession(tmp_path)
    try:
        url = session.start(preferred_port=occupied.server_port)
        assert int(url.rsplit(":", 1)[1]) != occupied.server_port
        with urlopen(url, timeout=3) as response:
            assert "암호화된 DH 키 교환" in response.read().decode("utf-8")
        with urlopen(url + "/api/health", timeout=3) as response:
            health = json.load(response)
        assert health["application"] == "crypto-dh-lab"
        assert launcher.existing_url(tmp_path / "launcher.json") == url
    finally:
        session.stop()
        occupied.server_close()
    assert not (tmp_path / "launcher.json").exists()
    assert not session.thread.is_alive()


def test_instance_lock_blocks_duplicate_and_releases_on_exit(tmp_path):
    import launcher

    first = launcher.InstanceLock(tmp_path / "launcher.lock")
    duplicate = launcher.InstanceLock(tmp_path / "launcher.lock")
    assert first.acquire()
    try:
        assert not duplicate.acquire()
    finally:
        first.release()
    assert duplicate.acquire()
    duplicate.release()


@pytest.mark.parametrize("state", [
    {"url": "https://example.com", "instance": "fake"},
    {"url": "http://127.0.0.1:1", "instance": "fake"},
    {"url": "file:///C:/secret", "instance": "fake"},
])
def test_stale_or_nonlocal_instance_is_never_opened(tmp_path, state):
    import launcher

    path = tmp_path / "launcher.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    assert launcher.existing_url(path) is None
