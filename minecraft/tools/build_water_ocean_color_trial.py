#!/usr/bin/env python3
"""Build a colored, low-transparency ocean-photo water trial (Pillow required).

Run from the repository root. This is a texture pack, not a shader.
"""
import json
import zipfile
from PIL import Image, ImageOps
from build_water_fancy_experiment import ROOT, SIZE, FRAMES, OVERLAP, match_edges
from build_water_ocean_trial import SOURCE, wave_frame as wave_channel

DEST = ROOT / 'realistic-water-ocean-color-trial'
TARGET = ROOT / 'realistic-water-ocean-color-trial.mcpack'
HEADER_UUID = '08b7f0b7-df9f-4529-ac1d-f25b9108fdf3'
MODULE_UUID = '6cd8513c-dd6d-4b53-b6a5-a218c53070c6'
STILL_ALPHA = 246
FLOW_ALPHA = 250


def color_tile(source=SOURCE):
    """Keep photo RGB values in the interior, blending only the borders."""
    extent = SIZE + 2 * OVERLAP
    with Image.open(source) as src:
        photo = ImageOps.fit(ImageOps.exif_transpose(src).convert('RGB'),
                             (extent, extent), Image.Resampling.LANCZOS)
    horizontal = photo.crop((OVERLAP, 0, OVERLAP + SIZE, extent))
    for d in range(OVERLAP):
        t = 1 - d / OVERLAP
        alpha = .5 * t * t * (3 - 2*t)
        for x, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sx = x + OVERLAP
            a = photo.crop((sx, 0, sx + 1, extent))
            b = photo.crop((sx + offset, 0, sx + offset + 1, extent))
            horizontal.paste(Image.blend(a, b, alpha), (x, 0))
    tile = horizontal.crop((0, OVERLAP, SIZE, OVERLAP + SIZE))
    for d in range(OVERLAP):
        t = 1 - d / OVERLAP
        alpha = .5 * t * t * (3 - 2*t)
        for y, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            sy = y + OVERLAP
            a = horizontal.crop((0, sy, SIZE, sy + 1))
            b = horizontal.crop((0, sy + offset, SIZE, sy + offset + 1))
            tile.paste(Image.blend(a, b, alpha), (0, y))
    return match_edges(tile)


def wave_frame(tile, index):
    # Reuse the identical per-channel mesh from the prior stronger-wave trial.
    return Image.merge('RGB', tuple(wave_channel(channel, index) for channel in tile.split()))


def make_sheets(tile):
    still = Image.new('RGBA', (SIZE, SIZE * FRAMES))
    flow = Image.new('RGBA', (2*SIZE, 2*SIZE*FRAMES))
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
    still, flow = make_sheets(color_tile())
    still.save(textures / 'water_still_grey.png', optimize=True)
    flow.save(textures / 'water_flow_grey.png', optimize=True)
    manifest = {
        'format_version': 2,
        'header': {'name': 'Вода — тёмный океан (цветной тест)',
                   'description': 'Цветная фотография и слабая прозрачность; без расчёта глубины',
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
