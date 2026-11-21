#!/usr/bin/env python3
"""Package optional dynamic behavior and matching resources as an .mcaddon."""
import io
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
resource = root / 'realistic-sounds'
behavior = root / 'living-world-behavior'
r = json.loads((resource / 'manifest.json').read_text())['header']
b = json.loads((behavior / 'manifest.json').read_text())
assert {'uuid': r['uuid'], 'version': r['version']} in b['dependencies']
behavior_archive = io.BytesIO()
with zipfile.ZipFile(behavior_archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as pack:
    for path in sorted(behavior.rglob('*')):
        if path.is_file():
            pack.write(path, path.relative_to(behavior).as_posix())
with zipfile.ZipFile(root / 'living-world-nature.mcaddon', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as out:
    out.writestr('living-world-behavior.mcpack', behavior_archive.getvalue())
    out.write(root / 'realistic-sounds.mcpack', 'realistic-sounds.mcpack')
print('Built living-world-nature.mcaddon')
