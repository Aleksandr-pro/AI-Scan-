#!/usr/bin/env python3
"""Create a photo-derived animated surface pack plus separate caustics preview.

Run from repo root; requires Pillow. No projected caustics or depth detection.
"""
import json
import zipfile
from pathlib import Path
from PIL import Image
from build_water_fancy_experiment import SIZE, FRAMES, match_edges
from build_water_ocean_color_trial import color_tile, wave_frame
from build_water_neutral_biomes import BASE_BIOMES

ROOT = Path('minecraft')
SOURCE_SURFACE = ROOT / 'water-reference/surface_source.png'
SOURCE_DEEP = ROOT / 'water-reference/deep_surface_source.png'
SOURCE_CAUSTICS = ROOT / 'water-reference/caustics_source.png'
DEST = ROOT / 'realistic-water-three-photos'
TARGET = ROOT / 'realistic-water-three-photos.mcpack'
CAUSTICS_STRIP = ROOT / 'water-caustics-preview-strip.png'
CAUSTICS_GIF = ROOT / 'water-caustics-preview.gif'
HEADER_UUID = 'b4b56257-15a1-4708-8f16-48093cc117b3'
MODULE_UUID = '86b31c20-b3fa-4db8-b24e-c46eabfa8b83'
STILL_ALPHA = 230
FLOW_ALPHA = 240
SURFACE_OPACITY = .92
DEEP_BLEND = .25


def surface_tile():
    # A single global surface; this blend does not represent actual depth.
    return match_edges(Image.blend(color_tile(SOURCE_SURFACE), color_tile(SOURCE_DEEP), DEEP_BLEND))


def sheets(tile):
    still = Image.new('RGBA', (SIZE, SIZE * FRAMES))
    flow = Image.new('RGBA', (2 * SIZE, 2 * SIZE * FRAMES))
    for i in range(FRAMES):
        frame = wave_frame(tile, i).convert('RGBA')
        frame.putalpha(STILL_ALPHA)
        still.paste(frame, (0, i * SIZE))
        frame.putalpha(FLOW_ALPHA)
        for y in (0, SIZE):
            for x in (0, SIZE):
                flow.paste(frame, (x, i * 2 * SIZE + y))
    return still, flow


def make_caustics_preview():
    # Separate illustration only. Not a game material or actual projected light.
    tile = color_tile(SOURCE_CAUSTICS)
    frames = [wave_frame(tile, i) for i in range(FRAMES)]
    strip = Image.new('RGB', (SIZE, SIZE * FRAMES))
    for i, frame in enumerate(frames):
        strip.paste(frame, (0, i * SIZE))
    strip.save(CAUSTICS_STRIP, optimize=True)
    frames[0].save(CAUSTICS_GIF, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=False)


def main():
    textures = DEST / 'textures/blocks'
    biomes = DEST / 'biomes'
    textures.mkdir(parents=True, exist_ok=True)
    biomes.mkdir(parents=True, exist_ok=True)
    still, flow = sheets(surface_tile())
    still.save(textures / 'water_still_grey.png', optimize=True)
    flow.save(textures / 'water_flow_grey.png', optimize=True)
    names = ['textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png']
    originals = sorted(BASE_BIOMES.glob('*.client_biome.json'))
    if len(originals) != 88:
        raise ValueError(f'Expected 88 client biomes, found {len(originals)}')
    for src in originals:
        biome = json.loads(src.read_text(encoding='utf-8'))
        appearance = biome['minecraft:client_biome']['components']['minecraft:water_appearance']
        appearance['surface_color'] = '#FFFFFF'
        appearance['surface_opacity'] = SURFACE_OPACITY
        (biomes / src.name).write_text(json.dumps(biome, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        names.append('biomes/' + src.name)
    manifest = {
        'format_version': 2,
        'header': {'name': 'Вода — тёмная рябь (тест)',
                   'description': 'Анимированное фото, немного прозрачности, нейтральные биомы',
                   'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'resources', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    names.append('manifest.json')
    found = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    if found != set(names):
        raise ValueError(f'Unexpected files: {found ^ set(names)}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            archive.write(DEST / name, name)
    make_caustics_preview()
    print(f'Built {TARGET}, {CAUSTICS_STRIP} and {CAUSTICS_GIF}')


if __name__ == '__main__':
    main()
