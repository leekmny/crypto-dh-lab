"""Collect license texts from the installed build environment for redistribution."""
from importlib.metadata import distribution
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
output = root / 'THIRD_PARTY_NOTICES.txt'
sections = ['CryptoDHLab Windows distribution: third-party license notices\n']
for name in ('cryptography', 'cffi', 'pycparser', 'pytest', 'pluggy', 'packaging',
             'iniconfig', 'pygments', 'colorama', 'pyinstaller'):
    package = distribution(name)
    sections.append(f'\n=== {package.metadata["Name"]} {package.version} ===\n')
    for path in package.files or ():
        if any(word in path.name.lower() for word in ('license', 'copying', 'notice')):
            file = Path(package.locate_file(path))
            if file.is_file():
                sections.append(f'\n--- {path} ---\n' + file.read_text(encoding='utf-8', errors='replace'))
python_root = Path(sys.base_prefix)
for file in [python_root / 'LICENSE.txt', *list((python_root / 'tcl').glob('*/license.terms'))]:
    if file.exists():
        sections.append(f'\n=== Python / Tcl-Tk: {file.name} ===\n' + file.read_text(encoding='utf-8', errors='replace'))
output.write_text('\n'.join(sections), encoding='utf-8')
print(output)
