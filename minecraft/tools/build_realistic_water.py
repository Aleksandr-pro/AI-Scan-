#!/usr/bin/env python3
"""Package the two separately selectable water resource packs."""
import zipfile
from pathlib import Path

root = Path('minecraft')
for state in ('calm', 'rough'):
    folder = root / 'realistic-water' / state
    target = root / f'realistic-water-{state}.mcpack'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())
    print(f'Built {target}')
