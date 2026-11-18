"""Verify release CRC, contents and extracted file hashes before delivery."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
archive = root / 'dist/CryptoDHLab-Windows-x64.zip'
folder = root / 'dist/CryptoDHLab'
destination = root / 'verification/release-preview'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    names = [n.replace('\\', '/') for n in z.namelist() if not n.endswith('/')]
    assert len(names) == len(set(names))
    assert 'CryptoDHLab/WINDOWS-사용법.txt' in names
    assert not any('/.local/' in n or '/logs/' in n or n.endswith(('.key', '.sqlite', 'results.json', 'output.txt')) for n in names)
    for entry in z.infolist():
        target = (destination / entry.filename).resolve()
        assert target.is_relative_to(destination.resolve())
    z.extractall(destination)
    for name in names:
        path = Path(name).relative_to('CryptoDHLab')
        assert hashlib.sha256((folder / path).read_bytes()).digest() == hashlib.sha256((destination / name).read_bytes()).digest(), name
report = {'archive': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'bytes': archive.stat().st_size, 'files': len(names), 'crc': True,
          'all_file_hashes_match': True, 'no_historical_keys_or_logs': True}
(root / 'verification/archive-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
