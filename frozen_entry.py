"""Single Windows executable: launcher, allowlisted workers, or bundled pytest."""
from __future__ import annotations

import runpy
import sys

from runtime import RESOURCE_ROOT, WORKERS, ensure_streams


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    ensure_streams()
    if arguments[:1] == ["--worker"]:
        if len(arguments) < 2 or arguments[1] not in WORKERS:
            print("지원하지 않는 실험 프로세스입니다.", file=sys.stderr)
            return 2
        script = RESOURCE_ROOT / arguments[1]
        sys.argv = [str(script), *arguments[2:]]
        runpy.run_path(str(script), run_name="__main__")
        return 0
    if arguments[:1] == ["--pytest"]:
        sys.argv = ["pytest", *arguments[1:]]
        runpy.run_module("pytest", run_name="__main__", alter_sys=True)
        return 0
    from launcher import main as launch
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
