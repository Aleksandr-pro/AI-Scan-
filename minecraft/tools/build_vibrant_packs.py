#!/usr/bin/env python3
"""Build the separate VV effects pack and an optional compatible texture copy.

Run from the repository root. The original realistic-dirt.mcpack is read-only.
The compatibility copy has its own UUIDs and uses the same texture bytes.
"""
import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path('minecraft')
EFFECTS = ROOT / 'realistic-atmosphere'
EFFECTS_PACK = ROOT / 'realistic-atmosphere.mcpack'
TEXTURES_PACK = ROOT / 'realistic-dirt.mcpack'
COMPAT_PACK = ROOT / 'realistic-dirt-vibrant.mcpack'
HEADER_UUID = '0ebccbee-75cb-426d-b948-6feb971b8b49'
MODULE_UUID = '91afbd08-5c78-4267-84cd-555c5af0640e'


def main(textures_only=False):
    if not textures_only:
        with zipfile.ZipFile(EFFECTS_PACK, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(EFFECTS.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(EFFECTS))

    # Repackage the previously verified distribution, not the source tree:
    # its intentional duplicate-variant omissions and atlas remain unchanged.
    with zipfile.ZipFile(TEXTURES_PACK) as original, zipfile.ZipFile(COMPAT_PACK, 'w') as output:
        manifest = json.loads(original.read('manifest.json'))
        manifest['header']['name'] = 'Реалистичная земля и трава — VV'
        manifest['header']['description'] = 'Совместимая с Vibrant Visuals копия текстурпака'
        manifest['header']['uuid'] = HEADER_UUID
        manifest['header']['min_engine_version'] = [1, 21, 120]
        for module in manifest['modules']:
            if module['type'] == 'resources':
                module['uuid'] = MODULE_UUID
        manifest['capabilities'] = ['pbr']
        for item in original.infolist():
            data = original.read(item.filename)
            if item.filename == 'manifest.json':
                data = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            # Preserve entries and their compression type, but match the
            # main archive's lossless level 9 to stay within hosting limits.
            output.writestr(item, data, compresslevel=9)
    if textures_only:
        print(f'Built {COMPAT_PACK}; effects and original pack unchanged.')
    else:
        print(f'Built {EFFECTS_PACK} and {COMPAT_PACK}; original pack unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--textures-only', action='store_true', help='do not rebuild the separate effects pack')
    main(textures_only=parser.parse_args().textures_only)
