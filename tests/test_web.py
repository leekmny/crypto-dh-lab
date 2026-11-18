import functools
from http.server import ThreadingHTTPServer
import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

import main
from lab import run_experiment


@pytest.fixture
def web_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "run_experiment", functools.partial(run_experiment, tmp_path))
    service = main.LabService()
    server = ThreadingHTTPServer(("127.0.0.1", 0), main.handler_for(service))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", service
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    for job in service.jobs:
        job.join(timeout=15)


def post(url, data, headers=None):
    request = Request(url, data=json.dumps(data).encode(), headers={"Content-Type":"application/json", **(headers or {})})
    return urlopen(request, timeout=5)


@pytest.mark.case("T14", "웹 API 실제 프로세스 실행·이벤트·키 비공개")
def test_dashboard_starts_actual_processes(web_api):
    url, _ = web_api
    with post(url + "/api/runs", dict(mode="small", scenario="normal", message="웹에서 시작한 메시지")) as response:
        assert response.status == 202
        run_id = json.load(response)["run_id"]
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with urlopen(url + "/api/state", timeout=3) as response:
            state = json.load(response)
        if not state["running"]:
            break
        time.sleep(0.05)
    assert state["run_id"] == run_id and state["summary"]["success"]
    assert state["summary"]["independent_processes"]
    assert any(e["event"] == "app_received" for e in state["events"])
    with pytest.raises(HTTPError) as raised:
        urlopen(url + "/.local/keys/alice.key", timeout=2)
    assert raised.value.code == 404


@pytest.mark.case("T14", "웹 API 로컬 출처·스키마·경로 제한")
def test_dashboard_rejects_foreign_origin_and_bad_inputs(web_api):
    url, _ = web_api
    for path, data, headers, code in [
        ("/api/runs", {}, {}, 400),
        ("/api/runs", dict(mode="small", scenario="normal", message="안녕"), {"Origin":"http://untrusted.example"}, 403),
        ("/api/tests", {}, {"Host":"untrusted.example"}, 403),
    ]:
        with pytest.raises(HTTPError) as raised:
            post(url + path, data, headers)
        assert raised.value.code == code
    with pytest.raises(HTTPError) as raised:
        urlopen(url + "/api/state?run=../../secret", timeout=3)
    assert raised.value.code == 400
