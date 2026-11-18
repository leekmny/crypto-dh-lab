from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = []
for name in ('alice.py', 'bob.py', 'eve.py', 'main.py', 'runtime.py', 'frozen_entry.py', 'pytest.ini'):
    datas.append((str(root / name), '.'))
for directory, pattern in (('web', '*'), ('tests', '*.py'), ('tests/fixtures', '*.txt')):
    for path in (root / directory).glob(pattern):
        if path.is_file():
            datas.append((str(path), directory))
for name in ('generate_keys.py', 'run_tests.py'):
    datas.append((str(root / 'scripts' / name), 'scripts'))
for package in ('cryptography', 'pytest', 'pluggy', 'packaging', 'iniconfig', 'pygments'):
    datas += copy_metadata(package)
hidden = collect_submodules('protocol') + collect_submodules('_pytest') + ['pytest.__main__', 'scripts.generate_keys']
a = Analysis([str(root / 'frozen_entry.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['IPython', 'numpy', 'setuptools'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CryptoDHLab',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CryptoDHLab')
