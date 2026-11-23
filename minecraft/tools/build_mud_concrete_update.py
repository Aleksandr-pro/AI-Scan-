#!/usr/bin/env python3
"""Build the full Bedrock pack with mud, concrete and stripped-oak updates.

Run after prepare_mud_concrete.py, prepare_stripped_oak.py and optimize_png_lossless.py. Preserves all
other archive paths and replaces existing entries from the source tree. The
old full mcpack must exist; it remains the source of the omission list.
"""
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT=Path('minecraft')
SOURCE=ROOT/'realistic-dirt'
PACK=ROOT/'realistic-dirt.mcpack'
VERSION=[2,7,2]
NEW=('textures/blocks/packed_mud.png','textures/blocks/concrete_white.png',
     'textures/blocks/concrete_red.png','textures/blocks/stripped_oak_log.png')


def main():
    manifest_path=SOURCE/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['header']['version']=VERSION
    for module in manifest['modules']:module['version']=VERSION
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    terrain_path=SOURCE/'textures/terrain_texture.json'
    terrain=json.loads(terrain_path.read_text(encoding='utf-8'))
    terrain['texture_data']['packed_mud']={'textures':'textures/blocks/packed_mud'}
    terrain['texture_data']['white_concrete']={'textures':'textures/blocks/concrete_white'}
    terrain['texture_data']['red_concrete']={'textures':'textures/blocks/concrete_red'}
    terrain['texture_data']['stripped_oak_log_side']={'textures':'textures/blocks/stripped_oak_log'}
    terrain_path.write_text(json.dumps(terrain,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(PACK) as original:
        existing=set(original.namelist())
        expected=existing|set(NEW)
        # Fail rather than silently drop anything from the prior distribution.
        for name in expected:
            if not (SOURCE/name).is_file():raise FileNotFoundError(name)
        with tempfile.NamedTemporaryFile(dir=ROOT,delete=False,suffix='.tmp') as tmp:
            tmp_name=tmp.name
        try:
            with zipfile.ZipFile(tmp_name,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
                for name in sorted(expected):out.write(SOURCE/name,name)
            with zipfile.ZipFile(tmp_name) as check:
                if check.testzip() is not None or set(check.namelist())!=expected:raise ValueError('archive validation failed')
            os.replace(tmp_name,PACK)
        finally:
            if os.path.exists(tmp_name):os.unlink(tmp_name)
    print(f'{PACK}: {PACK.stat().st_size} bytes')

if __name__=='__main__':main()
