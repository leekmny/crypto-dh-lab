"""Exercise the built executable with an isolated profile and a system-only PATH."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent.parent
data = root / 'verification' / ('frozen-' + time.strftime('%Y%m%d-%H%M%S'))
data.mkdir(parents=True)
exe = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / 'dist/CryptoDHLab/CryptoDHLab.exe'
env = {**os.environ, 'DH_LAB_DATA_DIR': str(data), 'PATH': os.environ['SystemRoot'] + r'\System32'}
process = subprocess.Popen([str(exe)], cwd=data, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
print(f'PID={process.pid}\nDATA={data}', flush=True)
deadline = time.monotonic() + 20
while not (data / 'launcher.json').exists():
    assert process.poll() is None, 'EXE exited before server startup'
    assert time.monotonic() < deadline, 'server startup timeout'
    time.sleep(0.1)
instance = json.loads((data / 'launcher.json').read_text())
url = instance['url']
print('URL=' + url, flush=True)

def get(path='/api/state'):
    with urlopen(url + path, timeout=5) as response:
        return json.load(response)

def post(path, body):
    request = Request(url + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=5) as response:
        return json.load(response)

report = {'pid': process.pid, 'data': str(data), 'url': url, 'system_only_path': env['PATH'], 'experiments': []}
for mode in ('small', 'group14'):
    post('/api/runs', {'mode': mode, 'scenario': 'normal', 'message': 'EXE 검수 메시지'})
    deadline = time.monotonic() + 30
    while True:
        state = get()
        if not state['running']:
            break
        assert time.monotonic() < deadline
        time.sleep(0.1)
    assert state['summary']['success'] and state['summary']['independent_processes'], state
    report['experiments'].append(state['summary'])
    print(mode + ' normal exchange PASS', flush=True)
duplicate = subprocess.Popen([str(exe)], cwd=data, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
assert duplicate.wait(timeout=15) == 0
assert json.loads((data / 'launcher.json').read_text()) == instance
report['duplicate_reused_instance'] = True
post('/api/tests', {})
deadline = time.monotonic() + 170
while True:
    state = get()
    if not state['testing']:
        break
    assert time.monotonic() < deadline, 'bundled validation timeout'
    time.sleep(0.5)
report['test_exit'] = state['test_exit']
report['test_error'] = state.get('test_error')
report['tests'] = state['tests']
(data / 'smoke-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ('test_exit', 'test_error')}, ensure_ascii=False), flush=True)
assert state['test_exit'] == 0 and state['tests']['failed'] == 0, state.get('test_error')
print('BUNDLED VALIDATION PASS; close the native launcher to verify shutdown.', flush=True)
