"""A requested validation must report this run's result, including launch failures."""
import json
import threading

import pytest

import main


def report(path, *, passed=1, failed=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"time": "2026-11-18T01:00:00+00:00", "exit_code": int(bool(failed)),
                               "passed": passed, "failed": failed, "tests": []}), encoding="utf-8")


def worker_with_report(path, *, failed=0):
    # Replace only the costly nested full pytest process; keep filesystem/state behavior real.
    def launch(_script, _arguments, output):
        output.write_text("validation worker output", encoding="utf-8")
        report(path, failed=failed)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["time"] = "new-run"
        path.write_text(json.dumps(data), encoding="utf-8")
        return FinishedWorker(int(bool(failed)))
    return launch


class FinishedWorker:
    def __init__(self, exit_code):
        self.exit_code = exit_code

    def wait(self, timeout):
        return self.exit_code


@pytest.mark.case("T14", "첫 실험 전 검증의 출력 폴더와 최신 결과")
def test_validation_works_before_first_experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "start_process", worker_with_report(tmp_path / "tests/results.json"))
    service = main.LabService()
    service.test()
    service.jobs[-1].join(timeout=10)
    state = service.state()
    assert not state["testing"]
    assert state["test_exit"] == 0
    assert state["tests"]["time"] == "new-run"
    assert (tmp_path / "logs/pytest-server.out.txt").exists()


@pytest.mark.case("T14", "검증 시작 실패가 이전 성공 결과를 대체")
def test_validation_launch_failure_hides_old_success(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    report(tmp_path / "tests/results.json")

    def unavailable(*_args):
        raise OSError("verification worker unavailable")

    monkeypatch.setattr(main, "start_process", unavailable)
    service = main.LabService()
    service.test()
    service.jobs[-1].join(timeout=5)
    state = service.state()
    assert state["test_exit"] == 2
    assert "verification worker unavailable" in state["test_error"]
    assert state["tests"] is None


@pytest.mark.case("T14", "새 검증 중 이전 종료 코드와 보고서 비공개")
def test_active_validation_clears_old_status(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    report(tmp_path / "tests/results.json")
    started, finish = threading.Event(), threading.Event()

    def blocked_launcher(*_args):
        started.set()
        finish.wait(timeout=5)
        raise RuntimeError("validation interrupted")

    monkeypatch.setattr(main, "start_process", blocked_launcher)
    service = main.LabService()
    service.test_exit = 0
    service.test()
    try:
        assert started.wait(timeout=3)
        state = service.state()
        assert state["testing"]
        assert state["test_exit"] is None
        assert state["tests"] is None
    finally:
        finish.set()
        service.jobs[-1].join(timeout=5)


@pytest.mark.case("T14", "이번 검증에서 생성한 실패 보고서는 표시")
def test_validation_keeps_fresh_failure_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    report(tmp_path / "tests/results.json")
    monkeypatch.setattr(main, "start_process", worker_with_report(tmp_path / "tests/results.json", failed=1))
    service = main.LabService()
    service.test()
    service.jobs[-1].join(timeout=10)
    state = service.state()
    assert state["test_exit"] == 1
    assert state["tests"]["time"] == "new-run"
    assert state["tests"]["failed"] == 1


@pytest.mark.case("T14", "보고서를 만들지 못한 검증은 성공으로 표시하지 않음")
def test_validation_without_report_is_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    report(tmp_path / "tests/results.json")
    (tmp_path / "logs").mkdir()

    def missing_report(_script, _arguments, output):
        output.write_text("no report created", encoding="utf-8")
        return FinishedWorker(0)

    monkeypatch.setattr(main, "start_process", missing_report)
    service = main.LabService()
    service.test()
    service.jobs[-1].join(timeout=5)
    state = service.state()
    assert state["test_exit"] == 2
    assert state["test_error"]
    assert state["tests"] is None
