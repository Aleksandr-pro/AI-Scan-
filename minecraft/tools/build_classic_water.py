#!/usr/bin/env python3
"""Build two standalone animated water packs for the normal Bedrock renderer.

Run from the repository root: python3 minecraft/tools/build_classic_water.py
Requires Pillow. Sources are the two existing user images in water-reference.
No PBR maps, shaders, VV settings, biome files, or gameplay files are included.
"""
import json
import math
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageStat

ROOT = Path('minecraft')
BASE = ROOT / 'realistic-water-classic'
SIZE = 64
FRAMES = 32  # Matches the vanilla sample sheets' frame count.
PROFILES = {
    'calm': {
        'source': 'calm_color.png',
        'label': 'спокойная',
        'header': '8b71ab8c-c6a2-4b27-a785-f781a9f12656',
        'module': 'dbab8fc5-d012-4a22-b6a6-8b517366c6b5',
    },
    'rough': {
        'source': 'rough_color.jpg',
        'label': 'волнистая',
        'header': '7251ec81-25fd-4cc5-a132-2a4253473047',
        'module': '3826930a-8e8d-4a75-8ea5-954097e8325f',
    },
}


def match_outer_edges(image):
    # Match the outermost pixels exactly and taper the adjustment over four
    # pixels. The underlying periodic photo remains detailed in the interior.
    result = image.copy()
    for d in range(4):
        amount = 0.5 * (1 - d / 4) ** 2
        left = result.crop((d, 0, d + 1, SIZE))
        right = result.crop((SIZE - 1 - d, 0, SIZE - d, SIZE))
        result.paste(Image.blend(left, right, amount), (d, 0))
        result.paste(Image.blend(right, left, amount), (SIZE - 1 - d, 0))
    for d in range(4):
        amount = 0.5 * (1 - d / 4) ** 2
        top = result.crop((0, d, SIZE, d + 1))
        bottom = result.crop((0, SIZE - 1 - d, SIZE, SIZE - d))
        result.paste(Image.blend(top, bottom, amount), (0, d))
        result.paste(Image.blend(bottom, top, amount), (0, SIZE - 1 - d))
    return result


def prepare_tile(source):
    # Unlike the previous half-offset crossfade, overlapping a source margin
    # does not duplicate the photo at half a tile's width in both directions.
    overlap = 8
    extent = SIZE + 2 * overlap
    with Image.open(source) as src:
        photo = ImageOps.fit(src.convert('RGB'), (extent, extent), Image.Resampling.LANCZOS)
    horizontal = photo.crop((overlap, 0, overlap + SIZE, extent))
    for d in range(overlap):
        t = 1 - d / overlap
        alpha = .5 * t * t * (3 - 2 * t)
        for x, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sx = x + overlap
            a = photo.crop((sx, 0, sx + 1, extent))
            b = photo.crop((sx + offset, 0, sx + offset + 1, extent))
            horizontal.paste(Image.blend(a, b, alpha), (x, 0))
    tile = horizontal.crop((0, overlap, SIZE, overlap + SIZE))
    for d in range(overlap):
        t = 1 - d / overlap
        alpha = .5 * t * t * (3 - 2 * t)
        for y, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sy = y + overlap
            a = horizontal.crop((0, sy, SIZE, sy + 1))
            b = horizontal.crop((0, sy + offset, SIZE, sy + offset + 1))
            tile.paste(Image.blend(a, b, alpha), (0, y))
    # Soften intense, static photographic highlights and reduce long straight
    # bands. This is a best-effort mitigation, not connected textures.
    lut = [i if i <= 150 else round(150 + (i - 150) * .3) for i in range(256)]
    tile = tile.point(lut * 3)
    rotated = ImageChops.offset(tile.transpose(Image.Transpose.ROTATE_90), 13, 21)
    tile = ImageEnhance.Contrast(Image.blend(tile, rotated, .20)).enhance(.8)
    gray = tile.convert('L')
    luminance = gray.load()
    average = ImageStat.Stat(gray).mean[0]
    rows = [sum(luminance[x, y] for x in range(SIZE)) / SIZE for y in range(SIZE)]
    cols = [sum(luminance[x, y] for y in range(SIZE)) / SIZE for x in range(SIZE)]
    source_pixels = tile.load()
    result = Image.new('RGB', tile.size)
    output = result.load()
    for y in range(SIZE):
        for x in range(SIZE):
            correction = .8 * (rows[y] + cols[x] - 2 * average)
            output[x, y] = tuple(max(0, min(255, round(c - correction))) for c in source_pixels[x, y])
    return match_outer_edges(result)


def frame_for(tile, index):
    # Periodic low-amplitude warp instead of sliding an entire tile across
    # every block. It is still a visual effect, not simulated fluid physics.
    tiled = Image.new('RGB', (SIZE * 3, SIZE * 3))
    for x in range(3):
        for y in range(3):
            tiled.paste(tile, (x * SIZE, y * SIZE))
    phase = 2 * math.pi * (index % FRAMES) / FRAMES
    def point(x, y):
        dx = .9 * math.sin(2 * math.pi * y / SIZE + phase) + .55 * math.sin(phase)
        dy = .7 * math.sin(2 * math.pi * x / SIZE - phase)
        return x + SIZE + dx, y + SIZE + dy
    mesh = []
    for y in range(0, SIZE, 8):
        for x in range(0, SIZE, 8):
            x2, y2 = x + 8, y + 8
            quad = (*point(x, y), *point(x, y2), *point(x2, y2), *point(x2, y))
            mesh.append(((x, y, x2, y2), quad))
    warped = tiled.transform((SIZE, SIZE), Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)
    return match_outer_edges(warped)


def sheets(tile):
    still = Image.new('RGBA', (SIZE, SIZE * FRAMES))
    flow = Image.new('RGBA', (SIZE * 2, SIZE * 2 * FRAMES))
    for i in range(FRAMES):
        frame = frame_for(tile, i).convert('RGBA')
        # Match vanilla sample's alpha convention; exact appearance remains
        # subject to the engine, biome tint and the selected graphics mode.
        frame.putalpha(240)
        still.paste(frame, (0, i * SIZE))
        frame.putalpha(255)
        for x in (0, SIZE):
            for y in (0, SIZE):
                flow.paste(frame, (x, i * SIZE * 2 + y))
    return still, flow


def main():
    for profile, settings in PROFILES.items():
        dest = BASE / profile
        textures = dest / 'textures/blocks'
        textures.mkdir(parents=True, exist_ok=True)
        tile = prepare_tile(ROOT / 'water-reference' / settings['source'])
        still, flow = sheets(tile)
        still.save(textures / 'water_still_grey.png', optimize=True)
        flow.save(textures / 'water_flow_grey.png', optimize=True)
        manifest = {
            'format_version': 2,
            'header': {
                'name': f'Реалистичная вода — обычный режим, {settings["label"]}',
                'description': 'Экспериментальная анимированная текстура воды без Vibrant Visuals',
                'uuid': settings['header'], 'version': [1, 1, 0], 'min_engine_version': [1, 26, 30],
            },
            'modules': [{'type': 'resources', 'uuid': settings['module'], 'version': [1, 1, 0]}],
        }
        (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Do not write flipbook_textures.json: the vanilla definitions already
        # identify these files, and replacing that list can break other blocks.
        files = ('manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png')
        existing = {p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}
        if existing != set(files):
            raise ValueError(f'Unexpected files in {dest}: {existing - set(files)}')
        target = ROOT / f'realistic-water-classic-{profile}.mcpack'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in files:
                archive.write(dest / name, name)
        print(f'Built {target}')


if __name__ == '__main__':
    main()
