"""Resource locations and child commands shared by source and Windows builds."""
from __future__ import annotations

import os
from pathlib import Path
import sys


RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
if os.environ.get("DH_LAB_DATA_DIR"):
    DATA_ROOT = Path(os.environ["DH_LAB_DATA_DIR"]).expanduser().resolve()
elif getattr(sys, "frozen", False):
    DATA_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "CryptoDHLab"
else:
    DATA_ROOT = RESOURCE_ROOT

WORKERS = frozenset(("alice.py", "bob.py", "eve.py", "main.py", "scripts/run_tests.py", "scripts/generate_keys.py"))


def process_command(script: str, arguments=()) -> list[str]:
    if script not in WORKERS:
        raise ValueError("지원하지 않는 실험 프로세스입니다.")
    prefix = [sys.executable, "--worker", script] if getattr(sys, "frozen", False) else [sys.executable, "-u", str(RESOURCE_ROOT / script)]
    return [*prefix, *map(str, arguments)]


def pytest_command(arguments=()) -> list[str]:
    prefix = [sys.executable, "--pytest"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "pytest"]
    return [*prefix, *map(str, arguments)]


def _windows_redirected_stream(index: int, mode: str):
    """A windowed executable still receives pipe/file handles from Popen."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                      ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    handle = kernel.GetStdHandle(index & 0xFFFFFFFF)
    if handle in (None, 0, ctypes.c_void_p(-1).value):
        return None
    current = kernel.GetCurrentProcess()
    duplicate = wintypes.HANDLE()
    if not kernel.DuplicateHandle(current, handle, current, ctypes.byref(duplicate), 0, False, 2):
        return None
    flags = (os.O_RDONLY if mode == "r" else os.O_WRONLY) | os.O_BINARY
    try:
        descriptor = msvcrt.open_osfhandle(duplicate.value, flags)
        return os.fdopen(descriptor, mode, encoding="utf-8", errors="replace", buffering=1)
    except OSError:
        kernel.CloseHandle(duplicate)
        return None


def ensure_streams():
    for name, index, mode in (("stdin", -10, "r"), ("stdout", -11, "w"), ("stderr", -12, "w")):
        stream = getattr(sys, name)
        if stream is None:
            stream = _windows_redirected_stream(index, mode) or open(os.devnull, mode, encoding="utf-8")
            setattr(sys, name, stream)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
