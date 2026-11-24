#!/usr/bin/env python3
"""Build a reproducible, separate two-pack Bedrock addon without touching the main pack."""
from pathlib import Path
import io
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'snow-footprints'
TARGET = ROOT / 'snow-footprints.mcaddon'
PACKS = {
    'snow-footprints-resources.mcpack': ('resources', {
        'manifest.json', 'particles/footprint.json', 'textures/particle/aegis_snow_footprint.png'}),
    'snow-footprints-behavior.mcpack': ('behavior', {
        'manifest.json', 'scripts/main.js', 'scripts/footsteps.js'}),
}

def write_entry(archive, name, data, compression=zipfile.ZIP_DEFLATED):
    info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    info.compress_type = compression
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=compression, compresslevel=9 if compression else None)


def pack(directory, allowed):
    found = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if found != allowed:
        raise ValueError(f'Unexpected or missing files in {directory}: {found ^ allowed}')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name in sorted(allowed):
            write_entry(archive, name, (directory / name).read_bytes())
    return buffer.getvalue()


def main():
    with zipfile.ZipFile(TARGET, 'w') as archive:
        for name, (directory, allowed) in PACKS.items():
            write_entry(archive, name, pack(SOURCE / directory, allowed), zipfile.ZIP_STORED)
    print('Built', TARGET, 'bytes:', TARGET.stat().st_size)

if __name__ == '__main__':
    main()
