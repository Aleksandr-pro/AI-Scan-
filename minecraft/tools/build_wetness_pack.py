#!/usr/bin/env python3
"""Build two independent packs and a convenient .mcaddon bundle."""
import zipfile
from pathlib import Path

ROOT = Path('minecraft')
SOURCE = ROOT / 'rain-wetness'


def pack(folder, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())


bp = ROOT / 'rain-wetness-behavior.mcpack'
rp = ROOT / 'rain-wetness-resources.mcpack'
pack(SOURCE / 'behavior', bp)
pack(SOURCE / 'resources', rp)
with zipfile.ZipFile(ROOT / 'rain-wetness.mcaddon', 'w', zipfile.ZIP_STORED) as archive:
    archive.write(bp, bp.name)
    archive.write(rp, rp.name)
print('Built wetness behavior, resource packs and addon bundle.')
