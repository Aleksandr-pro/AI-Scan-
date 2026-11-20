#!/usr/bin/env python3
"""Build an experimental four-plane custom fern block add-on for Bedrock.

From repo root, run after prepare_fern.py. Never replaces or edits world blocks.
The geometry/alpha behavior must be tested in the target game and device.
"""
import io
import json
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from prepare_fern import OUTPUT as FERN, SIZE

ROOT = Path('minecraft')
ADDON = ROOT / 'fern-fan-addon'
RP = ADDON / 'resources'
BP = ADDON / 'behavior'
TARGET = ROOT / 'fern-fan-experiment.mcaddon'
RHEADER = 'a13d6dfb-1fc6-4ea8-99f0-66e50402cfee'
RMODULE = '6a35024b-8a16-44be-98ee-a5e06e9e387c'
BHEADER = 'd5990368-35dc-47a7-b84f-309633af4f9a'
BMODULE = 'a4fe8f62-8e0d-42ac-8d41-68da1a899145'
IDENTIFIER = 'aifern:fan_fern'
GEOMETRY = 'geometry.aifern.fan_fern'
TEXTURE = 'aifern_fan'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def make_atlas():
    fern = Image.open(FERN).convert('RGBA')
    left = np.linspace(1, 0, SIZE)
    left = np.clip((left - .20) / .35, 0, 1)  # overlapping center, fade tips
    layers = []
    for base, weight in ((fern, left), (fern, 1-left), (ImageOps.mirror(fern), left), (ImageOps.mirror(fern), 1-left)):
        data = np.array(base)
        data[..., 3] = np.rint(data[..., 3].astype(float) * weight[None, :]).astype(np.uint8)
        data[data[..., 3] == 0, :3] = 0
        layers.append(Image.fromarray(data, 'RGBA'))
    atlas = Image.new('RGBA', (SIZE*2, SIZE*2))
    for i, layer in enumerate(layers):
        atlas.paste(layer, ((i % 2)*SIZE, (i // 2)*SIZE))
    return atlas


def geometry():
    bones = []
    for i, angle in enumerate((0, 45, 90, 135)):
        uv = [(i % 2)*SIZE, (i // 2)*SIZE]
        # A single zero-thickness face, double-sided through alpha_test.
        bones.append({'name': f'plane_{i}', 'pivot': [0, 0, 0], 'rotation': [0, angle, 0],
                      'cubes': [{'origin': [-8, 0, 0], 'size': [16, 16, 0],
                                 'uv': {'north': {'uv': uv, 'uv_size': [SIZE, SIZE]}}}]})
    return {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': GEOMETRY, 'texture_width': SIZE*2, 'texture_height': SIZE*2,
                        'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, .5, 0]},
        'bones': bones}]}


def pack_bytes(directory):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(directory.rglob('*')):
            if file.is_file():
                archive.write(file, file.relative_to(directory).as_posix())
    return stream.getvalue()


def main():
    texture = RP / f'textures/blocks/{TEXTURE}.png'
    texture.parent.mkdir(parents=True, exist_ok=True)
    make_atlas().save(texture, optimize=True)
    write_json(RP / 'textures/terrain_texture.json', {'resource_pack_name': 'aifern', 'texture_name': 'atlas.terrain',
               'texture_data': {TEXTURE: {'textures': f'textures/blocks/{TEXTURE}'}}})
    write_json(RP / 'models/blocks/fern.geo.json', geometry())
    write_json(RP / 'manifest.json', {'format_version': 2,
        'header': {'name': 'Папоротник веером — ресурсы (тест)', 'description': 'Текстуры и четыре плоскости для отдельного блока',
                   'uuid': RHEADER, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'resources', 'uuid': RMODULE, 'version': [1, 0, 0]}]})
    write_json(BP / 'manifest.json', {'format_version': 2,
        'header': {'name': 'Папоротник веером — эксперимент', 'description': 'Добавляет отдельный блок, не заменяет ванильные растения',
                   'uuid': BHEADER, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'data', 'uuid': BMODULE, 'version': [1, 0, 0]}],
        'dependencies': [{'uuid': RHEADER, 'version': [1, 0, 0]}]})
    write_json(BP / 'blocks/fan_fern.json', {'format_version': '1.26.30', 'minecraft:block': {
        'description': {'identifier': IDENTIFIER, 'menu_category': {'category': 'nature'}},
        'components': {'minecraft:display_name': 'Папоротник веером (тест)',
            'minecraft:geometry': GEOMETRY,
            'minecraft:material_instances': {'*': {'texture': TEXTURE, 'render_method': 'alpha_test',
                                                   'ambient_occlusion': False, 'face_dimming': False}},
            'minecraft:collision_box': False,
            'minecraft:selection_box': {'origin': [-7, 0, -7], 'size': [14, 15, 14]},
            'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.1},
            'minecraft:light_dampening': 0}}})
    allowed_rp = {'manifest.json', 'textures/terrain_texture.json', f'textures/blocks/{TEXTURE}.png', 'models/blocks/fern.geo.json'}
    allowed_bp = {'manifest.json', 'blocks/fan_fern.json'}
    for directory, allowed in ((RP, allowed_rp), (BP, allowed_bp)):
        found = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        if found != allowed:
            raise ValueError(f'Unexpected files in {directory}: {found ^ allowed}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_STORED) as addon:
        addon.writestr('fern-fan-resources.mcpack', pack_bytes(RP))
        addon.writestr('fern-fan-behavior.mcpack', pack_bytes(BP))
    print(f'Built {TARGET}; existing ferns are not replaced.')


if __name__ == '__main__':
    main()
