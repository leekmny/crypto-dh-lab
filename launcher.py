"""Small Windows controller for the local cryptography teaching dashboard."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
import webbrowser

import main as dashboard
from runtime import DATA_ROOT, ensure_streams


class InstanceLock:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.stream = None

    def acquire(self):
        if self.stream is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self.stream = stream
        return True

    def release(self):
        stream, self.stream = self.stream, None
        if stream is None:
            return
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def existing_url(state_path: Path):
    """Only reopen a live instance of this application on loopback."""
    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        url, instance = state["url"], state["instance"]
        if not isinstance(url, str) or not isinstance(instance, str) or not instance:
            return None
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or
            parsed.username is not None or parsed.password is not None or parsed.path or
            parsed.query or parsed.fragment or not parsed.port or
            parsed.netloc != f"127.0.0.1:{parsed.port}"):
            return None
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        with opener.open(url + "/api/health", timeout=0.5) as response:
            health = json.loads(response.read(4096))
        if health.get("application") == "crypto-dh-lab" and health.get("instance") == instance:
            return url
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


class LauncherSession:
    def __init__(self, data_root=DATA_ROOT):
        self.data_root = Path(data_root)
        self.service = dashboard.LabService()
        self.service.instance_id = secrets.token_hex(16)
        self.server = None
        self.thread = None
        self.url = None

    def start(self, preferred_port=8765):
        self.data_root.mkdir(parents=True, exist_ok=True)
        try:
            server = _LocalServer(("127.0.0.1", preferred_port), dashboard.handler_for(self.service))
        except OSError:
            server = _LocalServer(("127.0.0.1", 0), dashboard.handler_for(self.service))
        server.daemon_threads = True
        self.server = server
        self.url = f"http://127.0.0.1:{server.server_port}"
        self.thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1},
                                       name="로컬 실습 대시보드", daemon=True)
        self.thread.start()
        state = {"url": self.url, "instance": self.service.instance_id}
        (self.data_root / "launcher.json").write_text(json.dumps(state), encoding="utf-8")
        return self.url

    def stop(self):
        server, self.server = self.server, None
        if server is not None:
            server.shutdown()
            server.server_close()
        if self.thread is not None:
            self.thread.join()
        for job in list(self.service.jobs):
            job.join()
        state_path = self.data_root / "launcher.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("instance") == self.service.instance_id:
                state_path.unlink(missing_ok=True)
        except (OSError, ValueError, AttributeError):
            pass


def _show_error(title, message):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message, parent=root)
    root.destroy()


def main():
    ensure_streams()
    lock = InstanceLock(DATA_ROOT / "launcher.lock")
    session = None
    try:
        if not lock.acquire():
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                url = existing_url(DATA_ROOT / "launcher.json")
                if url:
                    if not webbrowser.open(url):
                        _show_error("실습 화면 열기", f"브라우저 주소창에 다음 주소를 입력하세요.\n\n{url}")
                    return 0
                time.sleep(0.1)
            _show_error("실험실 실행 중", "기존 실험실이 시작 또는 종료 중입니다. 잠시 후 다시 실행하세요.")
            return 2

        session = LauncherSession()
        url = session.start()
        import tkinter as tk
        from tkinter import messagebox, ttk
        root = tk.Tk()
        root.title("암호 프로토콜 실험실")
        root.geometry("500x330")
        root.minsize(500, 330)
        root.configure(background="#f2f5fb")
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Lab.TFrame", background="#f2f5fb")
        style.configure("Lab.TLabel", background="#f2f5fb", font=("맑은 고딕", 10))
        style.configure("Title.TLabel", background="#f2f5fb", foreground="#172a45", font=("맑은 고딕", 18, "bold"))
        style.configure("Lab.TButton", font=("맑은 고딕", 10), padding=(10, 8))
        frame = ttk.Frame(root, style="Lab.TFrame", padding=(26, 22))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="암호 프로토콜 실험실", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="작은 수 계산부터 패킷 관찰까지, 차근차근 실습하세요.",
                  style="Lab.TLabel").pack(anchor="w", pady=(7, 12))
        status = tk.StringVar(value="실행 중 · 브라우저에서 실험을 시작할 수 있습니다.")
        ttk.Label(frame, textvariable=status, style="Lab.TLabel").pack(anchor="w", pady=(0, 7))
        address = ttk.Entry(frame, font=("맑은 고딕", 11), state="readonly")
        address_value = tk.StringVar(value=url)
        address.configure(textvariable=address_value)
        address.pack(fill="x", ipady=5)
        buttons = ttk.Frame(frame, style="Lab.TFrame")
        buttons.pack(fill="x", pady=(15, 10))

        def open_browser():
            if not webbrowser.open(url):
                messagebox.showinfo("실습 화면 열기", f"브라우저 주소창에 다음 주소를 입력하세요.\n\n{url}", parent=root)

        def open_records():
            try:
                (DATA_ROOT / "logs").mkdir(parents=True, exist_ok=True)
                os.startfile(str(DATA_ROOT / "logs"))
            except OSError as error:
                messagebox.showerror("기록 폴더 열기", str(error), parent=root)

        open_button = ttk.Button(buttons, text="실습 화면 열기", command=open_browser, style="Lab.TButton")
        open_button.pack(side="left", fill="x", expand=True)
        records_button = ttk.Button(buttons, text="기록 폴더 열기", command=open_records, style="Lab.TButton")
        records_button.pack(side="left", padx=(8, 0), fill="x", expand=True)
        closing = False

        def close():
            nonlocal closing
            if closing:
                return
            closing = True
            for button in (open_button, records_button, close_button):
                button.state(["disabled"])
            status.set("종료 중 · 진행 중인 실험과 검증을 정리하고 있습니다.")
            shutdown = threading.Thread(target=session.stop, name="실습 종료")
            shutdown.start()
            def finish():
                if shutdown.is_alive():
                    root.after(100, finish)
                else:
                    lock.release()
                    root.destroy()
            root.after(100, finish)

        close_button = ttk.Button(buttons, text="종료", command=close, style="Lab.TButton")
        close_button.pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="이 창을 닫으면 로컬 서버도 함께 종료됩니다.", style="Lab.TLabel").pack(anchor="w", pady=(9, 0))
        root.protocol("WM_DELETE_WINDOW", close)

        def refresh_status():
            if closing:
                return
            status.set("전체 검증 실행 중입니다." if session.service.testing else
                       "실제 TCP 실험 실행 중입니다." if session.service.running else
                       "실행 중 · 브라우저에서 실험을 시작할 수 있습니다.")
            root.after(500, refresh_status)
        root.after(500, refresh_status)
        root.after(250, open_browser)
        root.mainloop()
        return 0
    except Exception as error:
        _show_error("암호 프로토콜 실험실 실행 실패", str(error))
        return 2
    finally:
        if session is not None:
            session.stop()
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
