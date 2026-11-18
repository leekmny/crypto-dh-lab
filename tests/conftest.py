import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from runtime import DATA_ROOT
RESULTS = []


def pytest_collection_modifyitems(items):
    RESULTS.clear()
    for item in items:
        marker = item.get_closest_marker("case")
        if marker:
            item.user_properties.extend([("code", marker.args[0]), ("label", marker.args[1])])


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.failed):
        properties = dict(report.user_properties)
        RESULTS.append(dict(test=report.nodeid, code=properties.get("code", "기타"), label=properties.get("label", report.nodeid),
                            outcome=report.outcome, duration=round(report.duration, 4),
                            reason=str(report.longrepr) if report.failed else ""))


def pytest_sessionfinish(session, exitstatus):
    data = dict(time=datetime.now(timezone.utc).isoformat(), exit_code=int(exitstatus), python=sys.version.split()[0],
                os=platform.platform(), cryptography=importlib.metadata.version("cryptography"),
                pytest=pytest.__version__, passed=sum(t["outcome"] == "passed" for t in RESULTS),
                failed=sum(t["outcome"] == "failed" for t in RESULTS), tests=RESULTS)
    (DATA_ROOT / "tests").mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "tests/results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("=", "실제 실행 검증 요약")
    grouped = {}
    for result in RESULTS:
        grouped.setdefault(result["code"], []).append(result)
    for code, results in sorted(grouped.items()):
        passed = all(row["outcome"] == "passed" for row in results)
        terminalreporter.write_line(f"[{'PASS' if passed else 'FAIL'}] {code} {results[0]['label']} ({len(results)}개 검사)")
