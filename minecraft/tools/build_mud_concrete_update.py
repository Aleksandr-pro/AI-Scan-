#!/usr/bin/env python3
"""Build the full Bedrock pack with the prepared photographic block textures.

Run after prepare_mud_concrete.py, prepare_stripped_oak.py,
prepare_stained_glass_panes.py, prepare_andesite.py, prepare_pot_shelf.py,
prepare_snow_normal.py and optimize_png_lossless.py as needed. Preserves all
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
VERSION=[2,7,6]
COLORS=('black','white','pink')
NEW=('textures/blocks/packed_mud.png','textures/blocks/concrete_white.png',
     'textures/blocks/concrete_red.png','textures/blocks/stripped_oak_log.png',
     'textures/blocks/stone_andesite.png','textures/blocks/flower_pot.png',
     'textures/blocks/oak_shelf.png',
     *(f'textures/blocks/photo_stained_glass_{c}_pane_edge.png' for c in COLORS))


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
    # Vanilla uses the same texture for natural andesite, its slabs, stairs
    # and wall. The polished-andesite texture remains untouched.
    for key in ('andesite','andesite_slab','andesite_wall'):
        terrain['texture_data'][key]={'textures':'textures/blocks/stone_andesite'}
    terrain['texture_data']['flower_pot']={'textures':'textures/blocks/flower_pot'}
    terrain['texture_data']['oak_shelf']={'textures':['textures/blocks/oak_shelf']}
    for color in COLORS:
        key=f'photo_stained_glass_{color}_pane_edge'
        terrain['texture_data'][key]={'textures':f'textures/blocks/{key}'}
    terrain_path.write_text(json.dumps(terrain,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    blocks_path=SOURCE/'blocks.json'
    blocks=json.loads(blocks_path.read_text(encoding='utf-8'))
    for color in COLORS:
        face=f'photo_stained_glass_{color}'
        edge=f'{face}_pane_edge'
        # Preserve Bedrock samples' pane face assignment, including the
        # special east slot. Change only the three modern coloured panes.
        blocks[f'{color}_stained_glass_pane']={
            'sound':'glass', 'textures':{
                'down':face, 'east':edge, 'north':face, 'south':face,
                'up':face, 'west':face}}
    blocks_path.write_text(json.dumps(blocks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
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
