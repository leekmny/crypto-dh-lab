"""127.0.0.1 전용 HTTP 대시보드 및 실제 실험 실행 API."""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
from urllib.parse import urlsplit, parse_qs
import webbrowser

from lab import ROOT, SCENARIOS, run_experiment, experiment_events, start_process
from protocol.messages import decode_json
from protocol.errors import ProtocolError
from protocol.session import ALICE_MESSAGE
from scripts.generate_keys import generate
from runtime import RESOURCE_ROOT, ensure_streams


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class LabService:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.testing = False
        self.test_exit = None
        self.jobs = []
        self.latest = None
        existing = sorted((ROOT / "logs").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
        if existing:
            self.latest = existing[-1].parent.name

    def start(self, mode, scenario, message):
        if mode not in ("small", "group14") or scenario not in SCENARIOS:
            raise ValueError("지원하지 않는 모드 또는 시나리오입니다.")
        if not isinstance(message, str) or not 1 <= len(message.encode("utf-8")) <= 4096:
            raise ValueError("응용 메시지는 UTF-8 기준 1–4096바이트여야 합니다.")
        with self.lock:
            if self.running or self.testing:
                raise RuntimeError("이미 실험 또는 검증이 진행 중입니다.")
            self.running = True
            self.latest = secrets.token_hex(12)
            run_id = self.latest
        def job():
            try:
                run_experiment(mode=mode, scenario=scenario, message=message, run_id=run_id)
            finally:
                with self.lock:
                    self.running = False
        thread = threading.Thread(target=job, name="실제 TCP 실험")
        self.jobs.append(thread)
        thread.start()
        return run_id

    def test(self):
        with self.lock:
            if self.running or self.testing:
                raise RuntimeError("이미 실험 또는 검증이 진행 중입니다.")
            self.testing = True
            self.test_exit = None
            self.test_error = None
        def job():
            try:
                report = ROOT / "tests/results.json"
                report.unlink(missing_ok=True)
                output = ROOT / "logs/pytest-server.out.txt"
                output.parent.mkdir(parents=True, exist_ok=True)
                process = start_process("scripts/run_tests.py", [], output)
                try:
                    self.test_exit = process.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
                    self.test_exit = 2
                    self.test_error = "검증 제한 시간을 초과했습니다. 다시 실행하세요."
                if read_json(report) is None and self.test_error is None:
                    self.test_exit = self.test_exit or 2
                    self.test_error = "이번 검증의 결과 보고서를 만들지 못했습니다. 검증 로그를 확인하세요."
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.test_exit = 2
                self.test_error = "검증 실행 실패: " + str(error)
            finally:
                with self.lock:
                    self.testing = False
        thread = threading.Thread(target=job, name="실제 pytest 검증")
        self.jobs.append(thread)
        thread.start()

    def state(self, run_id=None):
        run_id = run_id or self.latest
        if run_id and not re.fullmatch(r"[0-9a-f]{24}", run_id):
            raise ValueError("실행 식별자 형식이 잘못되었습니다.")
        summary = read_json(ROOT / "logs" / run_id / "summary.json") if run_id else None
        events = experiment_events(ROOT, run_id) if run_id else []
        test_error = getattr(self, "test_error", None)
        tests = None if self.testing or test_error else read_json(ROOT / "tests/results.json")
        return dict(run_id=run_id, running=self.running, testing=self.testing, test_exit=self.test_exit,
                    test_error=test_error, summary=summary, events=events, tests=tests)


def handler_for(service):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(RESOURCE_ROOT / "web"), **kwargs)

        def log_message(self, *_):
            pass

        def allowed_host(self):
            port = self.server.server_address[1]
            return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            super().end_headers()

        def respond(self, data, code=200):
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.allowed_host():
                return self.respond({"error": "로컬 주소의 요청만 허용합니다."}, 403)
            parsed = urlsplit(self.path)
            if parsed.path == "/api/health":
                return self.respond({"application": "crypto-dh-lab", "instance": getattr(service, "instance_id", None)})
            if parsed.path in ("/api/state", "/api/export"):
                try:
                    run_id = parse_qs(parsed.query).get("run", [None])[0]
                    return self.respond(service.state(run_id))
                except ValueError as error:
                    return self.respond({"error": str(error)}, 400)
            if parsed.path not in ("/", "/index.html", "/style.css", "/app.js", "/animation.js", "/favicon.svg"):
                return self.respond({"error": "요청한 파일이 없습니다."}, 404)
            return super().do_GET()

        def do_POST(self):
            if not self.allowed_host():
                return self.respond({"error": "로컬 요청만 허용합니다."}, 403)
            port = self.server.server_address[1]
            origin = self.headers.get("Origin")
            if (origin is not None and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")) or self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.respond({"error": "다른 사이트의 실행 요청을 거부했습니다."}, 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("제한된 JSON 요청만 허용합니다.")
                self.connection.settimeout(3)
                body = decode_json(self.rfile.read(length))
                if self.path == "/api/runs":
                    if body.keys() != {"mode", "scenario", "message"}:
                        raise ValueError("실험 요청 필드가 잘못되었습니다.")
                    run_id = service.start(body["mode"], body["scenario"], body["message"])
                    return self.respond({"run_id": run_id}, 202)
                if self.path == "/api/tests" and body == {}:
                    service.test()
                    return self.respond({"message": "실제 pytest 실행을 시작했습니다."}, 202)
                return self.respond({"error": "지원하지 않는 API입니다."}, 404)
            except (ValueError, ProtocolError, TypeError) as error:
                return self.respond({"error": str(error)}, 400)
            except RuntimeError as error:
                return self.respond({"error": str(error)}, 409)
            except (OSError, TimeoutError):
                return self.respond({"error": "HTTP 요청 수신 제한 시간을 초과했습니다."}, 408)
    return Handler


def main():
    ensure_streams()
    parser = argparse.ArgumentParser(description="실제 암호화 DH 프로세스·TCP 실험실")
    parser.add_argument("--port", type=int, default=8765, help="로컬 대시보드 포트")
    parser.add_argument("--mode", choices=("small", "group14"), default="group14")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), default="normal")
    parser.add_argument("--cli", action="store_true", help="웹 서버 없이 단일 실제 실험")
    parser.add_argument("--auto-run", action="store_true", help="웹 서버와 함께 실제 실험 자동 시작")
    parser.add_argument("--open", action="store_true", help="브라우저 열기")
    args = parser.parse_args()
    generate(ROOT / ".local/keys")
    if args.cli:
        result = run_experiment(mode=args.mode, scenario=args.scenario)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 2
    if not 1 <= args.port <= 65535:
        parser.error("포트는 1–65535 사이여야 합니다.")
    service = LabService()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(service))
    except OSError:
        print("대시보드 포트를 사용할 수 없습니다. 다른 --port를 선택하세요.")
        return 2
    server.daemon_threads = True
    url = f"http://127.0.0.1:{args.port}"
    print(f"로컬 암호 실험실: {url}", flush=True)
    print("종료: Ctrl+C. 실제 키 원문은 화면과 로그에 표시하지 않습니다.", flush=True)
    if args.auto_run:
        service.start(args.mode, args.scenario, ALICE_MESSAGE)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("서버를 종료하고 실행 중인 프로세스 정리를 기다립니다.")
    finally:
        server.server_close()
        for thread in service.jobs:
            thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
