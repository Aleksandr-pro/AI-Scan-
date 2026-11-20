#!/usr/bin/env python3
"""Build a separate photo-derived water experiment for normal Bedrock graphics.

From the repository root: python3 minecraft/tools/build_water_fancy_experiment.py
Requires Pillow. Does not modify the previous classic or VV water packs.
The source is an oblique photo, not a seamless overhead water texture.
"""
import json
import math
import zipfile

from pathlib import Path
from PIL import Image, ImageOps, ImageStat

ROOT = Path('minecraft')
DEST = ROOT / 'realistic-water-fancy-experiment'
TARGET = ROOT / 'realistic-water-fancy-experiment.mcpack'
SOURCE = ROOT / 'water-reference/rough_color.jpg'
HEADER_UUID = 'e8526301-e4af-4b0a-b676-f630af028e13'
MODULE_UUID = '6dc5b1b5-98d5-4b33-b38d-6d1922c3a4ac'
SIZE = 128
FRAMES = 32
OVERLAP = 16
STILL_ALPHA = 208
FLOW_ALPHA = 225


def match_edges(image):
    """Blend four pixels across the periodic boundary, preserving interior."""
    n = image.width
    result = image.copy()
    for d in range(4):
        amount = .5 * (1 - d / 4) ** 2
        left = result.crop((d, 0, d + 1, n))
        right = result.crop((n - 1 - d, 0, n - d, n))
        result.paste(Image.blend(left, right, amount), (d, 0))
        result.paste(Image.blend(right, left, amount), (n - 1 - d, 0))
    for d in range(4):
        amount = .5 * (1 - d / 4) ** 2
        top = result.crop((0, d, n, d + 1))
        bottom = result.crop((0, n - 1 - d, n, n - d))
        result.paste(Image.blend(top, bottom, amount), (0, d))
        result.paste(Image.blend(bottom, top, amount), (0, n - 1 - d))
    return result


def prepare_tile(source=SOURCE):
    """Keep photographic ripple detail while toning down repeated bands.

    Water uses biome tint; neutral grey avoids baking blue on top of that tint.
    Brightness/transparency are experimental and may be interpreted differently
    by the engine, so this is not a calibrated recreation of the reference.
    """
    extent = SIZE + OVERLAP * 2
    with Image.open(source) as src:
        photo = ImageOps.fit(ImageOps.exif_transpose(src).convert('L'),
                             (extent, extent), Image.Resampling.LANCZOS)
    horizontal = photo.crop((OVERLAP, 0, OVERLAP + SIZE, extent))
    for d in range(OVERLAP):
        t = 1 - d / OVERLAP
        alpha = .5 * t * t * (3 - 2 * t)
        for x, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sx = x + OVERLAP
            a = photo.crop((sx, 0, sx + 1, extent))
            b = photo.crop((sx + offset, 0, sx + offset + 1, extent))
            horizontal.paste(Image.blend(a, b, alpha), (x, 0))
    tile = horizontal.crop((0, OVERLAP, SIZE, OVERLAP + SIZE))
    for d in range(OVERLAP):
        t = 1 - d / OVERLAP
        alpha = .5 * t * t * (3 - 2 * t)
        for y, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sy = y + OVERLAP
            a = horizontal.crop((0, sy, SIZE, sy + 1))
            b = horizontal.crop((0, sy + offset, SIZE, sy + offset + 1))
            tile.paste(Image.blend(a, b, alpha), (0, y))
    gray = tile.load()
    avg = ImageStat.Stat(tile).mean[0]
    rows = [sum(gray[x, y] for x in range(SIZE)) / SIZE for y in range(SIZE)]
    cols = [sum(gray[x, y] for y in range(SIZE)) / SIZE for x in range(SIZE)]
    result = Image.new('L', tile.size)
    result.putdata([
        max(145, min(225, round(190 + .55 * (gray[x, y] - avg - .65 * (rows[y] + cols[x] - 2 * avg)))))
        for y in range(SIZE) for x in range(SIZE)
    ])
    return match_edges(result)


def wave_frame(photo_tile, index):
    """Warp the photo gently with a looping mesh, not simulated wave physics."""
    tiled = Image.new('L', (SIZE * 3, SIZE * 3))
    for x in range(3):
        for y in range(3):
            tiled.paste(photo_tile, (x * SIZE, y * SIZE))
    phase = 2 * math.pi * (index % FRAMES) / FRAMES
    def point(x, y):
        dx = 1.8 * math.sin(2 * math.pi * y / SIZE + phase) + 1.1 * math.sin(phase)
        dy = 1.4 * math.sin(2 * math.pi * x / SIZE - phase)
        return x + SIZE + dx, y + SIZE + dy
    mesh = []
    for y in range(0, SIZE, 16):
        for x in range(0, SIZE, 16):
            x2, y2 = x + 16, y + 16
            quad = (*point(x, y), *point(x, y2), *point(x2, y2), *point(x2, y))
            mesh.append(((x, y, x2, y2), quad))
    warped = tiled.transform((SIZE, SIZE), Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)
    return match_edges(warped)


def make_sheets(photo_tile):
    still = Image.new('RGBA', (SIZE, SIZE * FRAMES))
    flow = Image.new('RGBA', (2 * SIZE, 2 * SIZE * FRAMES))
    for i in range(FRAMES):
        rgba = wave_frame(photo_tile, i).convert('RGBA')
        rgba.putalpha(STILL_ALPHA)
        still.paste(rgba, (0, i * SIZE))
        rgba.putalpha(FLOW_ALPHA)
        # Vanilla's flow flipbook uses a twice-wide frame and replicate=2.
        for x in (0, SIZE):
            for y in (0, SIZE):
                flow.paste(rgba, (x, i * SIZE * 2 + y))
    return still, flow


def main():
    tex = DEST / 'textures/blocks'
    tex.mkdir(parents=True, exist_ok=True)
    still, flow = make_sheets(prepare_tile())
    still.save(tex / 'water_still_grey.png', optimize=True)
    flow.save(tex / 'water_flow_grey.png', optimize=True)
    manifest = {
        'format_version': 2,
        'header': {'name': 'Экспериментальная вода — красивый режим',
                   'description': 'Фототекстура воды без Vibrant Visuals',
                   'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'resources', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = ('manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png')
    actual = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    if actual != set(files):
        raise ValueError(f'Unexpected files in {DEST}: {actual - set(files)}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            archive.write(DEST / name, name)
    print(f'Built {TARGET}')


if __name__ == '__main__':
    main()
