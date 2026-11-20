#!/usr/bin/env python3
"""Build an independent animated water trial from the user's ocean photo.

Run from repo root with Pillow: python3 minecraft/tools/build_water_ocean_trial.py
The mesh warps a texture; it does not deform geometry or calculate water depth.
"""
import json
import math
import zipfile
from PIL import Image, ImageEnhance
from build_water_fancy_experiment import (
    ROOT, SIZE, FRAMES, STILL_ALPHA, FLOW_ALPHA, prepare_tile, match_edges,
)

SOURCE = ROOT / 'water-reference/ocean_waves.png'
DEST = ROOT / 'realistic-water-ocean-trial'
TARGET = ROOT / 'realistic-water-ocean-trial.mcpack'
HEADER_UUID = 'b9890490-610f-4e31-ae99-cf4263c15fa6'
MODULE_UUID = '341395d0-338b-4249-9d86-d0a2d84a785f'


def ocean_tile(source=SOURCE):
    # Bedrock tints the grey water texture by biome. Brightness is deliberately
    # adapted from the dark source, so the original blue is not reproduced.
    return match_edges(ImageEnhance.Contrast(prepare_tile(source)).enhance(1.2))


def wave_frame(tile, index):
    """Periodic displacement, twice the earlier trial's mesh amplitude."""
    tiled = Image.new('L', (3 * SIZE, 3 * SIZE))
    for y in range(3):
        for x in range(3):
            tiled.paste(tile, (x * SIZE, y * SIZE))
    phase = 2 * math.pi * (index % FRAMES) / FRAMES
    def point(x, y):
        dx = 4.8 * math.sin(2 * math.pi * y / SIZE + phase) + 2.8 * math.sin(phase)
        dy = 3.6 * math.sin(2 * math.pi * x / SIZE - phase)
        return x + SIZE + dx, y + SIZE + dy
    mesh = []
    for y in range(0, SIZE, 16):
        for x in range(0, SIZE, 16):
            x2, y2 = x + 16, y + 16
            mesh.append(((x, y, x2, y2), (*point(x, y), *point(x, y2), *point(x2, y2), *point(x2, y))))
    return match_edges(tiled.transform((SIZE, SIZE), Image.Transform.MESH, mesh, Image.Resampling.BICUBIC))


def make_sheets(tile):
    still = Image.new('RGBA', (SIZE, SIZE * FRAMES))
    flow = Image.new('RGBA', (2 * SIZE, 2 * SIZE * FRAMES))
    for i in range(FRAMES):
        rgba = wave_frame(tile, i).convert('RGBA')
        rgba.putalpha(STILL_ALPHA)
        still.paste(rgba, (0, i * SIZE))
        rgba.putalpha(FLOW_ALPHA)
        for y in (0, SIZE):
            for x in (0, SIZE):
                flow.paste(rgba, (x, i * 2 * SIZE + y))
    return still, flow


def main():
    textures = DEST / 'textures/blocks'
    textures.mkdir(parents=True, exist_ok=True)
    still, flow = make_sheets(ocean_tile())
    still.save(textures / 'water_still_grey.png', optimize=True)
    flow.save(textures / 'water_flow_grey.png', optimize=True)
    manifest = {
        'format_version': 2,
        'header': {'name': 'Вода — океанские волны (тест)',
                   'description': 'Фототекстура и усиленная анимация без VV; без расчёта глубины',
                   'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'resources', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = ('manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png')
    actual = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    if actual != set(files):
        raise ValueError(f'Unexpected files in {DEST}: {actual ^ set(files)}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            archive.write(DEST / name, name)
    print(f'Built {TARGET}')


if __name__ == '__main__':
    main()
