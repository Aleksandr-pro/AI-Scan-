#!/usr/bin/env python3
"""Assemble a single importable bundle, without modifying the existing packs.

Outputs a large, deliberately Git-ignored .mcaddon containing three nested
resource/behavior packs. Nothing here edits a Minecraft world. The grass-flow
behavior still creates ONLY an explicit test platform in empty space.
"""
from pathlib import Path
import io
import json
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'realistic-dirt.mcpack'
FLOW = ROOT / 'grass-flow-experiment.mcaddon'
OUTPUT = ROOT / 'realistic-complete-grassflow.mcaddon'
BASE_ID = 'c82fb06e-bbe1-4f64-b6aa-c3136b61a026'
FLOW_RP_ID = '07e733e9-d5e9-4133-b826-29571da21290'
FLOW_BP_ID = '06cce6ab-8293-43d2-af08-b21f4b09e986'
BASE_VERSION = [2, 6, 1]
FLOW_VERSION = [1, 0, 1]


def transform_pack(source, output, kind):
    with zipfile.ZipFile(source) as original:
        manifest = json.loads(original.read('manifest.json'))
        expected = {'base': BASE_ID, 'flow_resources': FLOW_RP_ID, 'flow_behavior': FLOW_BP_ID}[kind]
        if manifest['header']['uuid'] != expected:
            raise ValueError(f'Unexpected {kind} pack UUID')
        version = BASE_VERSION if kind == 'base' else FLOW_VERSION
        manifest['header']['version'] = version
        for module in manifest['modules']:
            module['version'] = version
        if kind == 'base':
            manifest['header']['description'] = 'Полный текстурпак для комплекта с экспериментом Живая почва'
        if kind == 'flow_behavior':
            matches = [d for d in manifest.get('dependencies', []) if d.get('uuid') == FLOW_RP_ID]
            if len(matches) != 1:
                raise ValueError('Expected a single grass-flow resource dependency')
            matches[0]['version'] = FLOW_VERSION
        new_manifest = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        with zipfile.ZipFile(output, 'w', allowZip64=True) as result:
            for info in original.infolist():
                payload = new_manifest if info.filename == 'manifest.json' else original.read(info)
                result.writestr(info, payload, compresslevel=9)


def main():
    # Temporary large nested archive stays outside the repo; only the final
    # package is written in the workspace. Zip is STORED to avoid recompressing
    # already-compressed .mcpack archives.
    with tempfile.TemporaryDirectory(prefix='grassflow-bundle-') as temp:
        temp = Path(temp)
        with zipfile.ZipFile(FLOW) as addon:
            names = ['grass-flow-resources.mcpack', 'grass-flow-behavior.mcpack']
            if set(addon.namelist()) != set(names):
                raise ValueError('Unexpected grass-flow addon contents')
            resource = io.BytesIO(addon.read(names[0]))
            behavior = io.BytesIO(addon.read(names[1]))
        packs = [('realistic-dirt.mcpack', BASE, 'base'),
                 ('grass-flow-resources.mcpack', resource, 'flow_resources'),
                 ('grass-flow-behavior.mcpack', behavior, 'flow_behavior')]
        with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_STORED, allowZip64=True) as bundle:
            for name, source, kind in packs:
                nested = temp / name
                transform_pack(source, nested, kind)
                bundle.write(nested, name)
                nested.unlink()
    print(f'Built {OUTPUT} ({OUTPUT.stat().st_size / 1024**2:.1f} MiB); vanilla terrain remains unchanged.')


if __name__ == '__main__':
    main()
