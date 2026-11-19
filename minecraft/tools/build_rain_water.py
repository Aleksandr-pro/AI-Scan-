#!/usr/bin/env python3
"""Package the standalone Bedrock behavior pack. Run from repository root."""
from pathlib import Path
import zipfile

source = Path('minecraft/realistic-rain-water')
output = Path('minecraft/realistic-rain-water.mcpack')
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(source.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(source).as_posix())
print(f'Built {output}')
