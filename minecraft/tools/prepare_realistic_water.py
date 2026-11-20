#!/usr/bin/env python3
"""Build two tiled, animated Bedrock water variants from user-supplied images.

The reference photographs already contain lighting; the normal screenshots are
not registered to them. This creates an approximation, not physical simulation.
Requires Pillow. Run from the repository root.
"""
import json
import math
import shutil
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path('minecraft')
REFERENCE = ROOT / 'water-reference'
OUT = ROOT / 'realistic-water'
FRAMES = 16
STATES = {
    'calm': {
        'color': 'calm_color.png', 'normal': 'calm_normal.jpg',
        'name': 'Реалистичная вода — спокойная',
        'header': '9fac423e-362a-48ba-850c-946762da5e1c',
        'module': 'cf28053a-b056-4026-a735-a591cab9fbbb',
        'depth': 0.12, 'frequency': 0.65, 'speed': 0.35, 'octaves': 3,
    },
    'rough': {
        'color': 'rough_color.jpg', 'normal': 'rough_normal.jpg',
        'name': 'Реалистичная вода — волнистая',
        'header': '6d829869-7e98-4497-b3c7-cdd5293166c2',
        'module': 'c6c63a35-6425-4534-a2cc-2238b339c2a5',
        'depth': 0.42, 'frequency': 0.95, 'speed': 0.85, 'octaves': 4,
    },
}


def square_crop(path, size):
    with Image.open(path) as im:
        im = im.convert('RGB')
        w, h = im.size
        side = min(w, h)
        # A central crop keeps aspect ratio; no perspective correction is implied.
        left, top = (w - side) // 2, (h - side) // 2
        return im.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)


def seamless(image):
    """Crossfade a half-offset copy, masking each copy's discontinuities.

    Source edges have zero weight at the tile boundary; the half-offset copy
    has zero weight at the central join. Unlike stretching a seam into a band,
    the fade retains wave texture throughout. Perspective remains approximate.
    """
    size = image.width
    weights = [round(255 * math.sin(math.pi * i / (size - 1)) ** 2) for i in range(size)]
    horizontal = Image.new('L', (size, size))
    horizontal.putdata(weights * size)
    out = Image.composite(image, ImageChops.offset(image, size // 2, 0), horizontal)
    vertical = horizontal.transpose(Image.Transpose.TRANSPOSE)
    return Image.composite(out, ImageChops.offset(out, 0, size // 2), vertical)


def normalize_map(image):
    """Neutralize screenshot tint, retain slopes, reconstruct unit normals."""
    avg = ImageStat.Stat(image).mean
    result = Image.new('RGB', image.size)
    output = []
    for r, g, _ in image.getdata():
        x = max(-0.68, min(0.68, (r - avg[0]) / 127.5 * 0.72))
        y = max(-0.68, min(0.68, (g - avg[1]) / 127.5 * 0.72))
        z = math.sqrt(max(0.01, 1 - x * x - y * y))
        output.append((round((x * 0.5 + 0.5) * 255), round((y * 0.5 + 0.5) * 255), round((z * 0.5 + 0.5) * 255)))
    result.putdata(output)
    return result


def soften_baked_highlights(image):
    # Do not advertise these photographic pixels as real reflections. Compress
    # the brightest clipped highlights so the game's dynamic lighting can show.
    lut = [i if i <= 175 else round(175 + (i - 175) * 0.35) for i in range(256)]
    return image.point(lut * 3)


def flipbook(tile, alpha):
    size = tile.width
    sheet = Image.new('RGBA', (size, size * FRAMES))
    tile = tile.convert('RGBA')
    tile.putalpha(alpha)
    for frame in range(FRAMES):
        # Equal cyclic offset in every layer keeps the supplied pair in sync.
        dx = round(frame * size / FRAMES)
        dy = round(size * 0.025 * math.sin(2 * math.pi * frame / FRAMES))
        sheet.paste(ImageChops.offset(tile, dx, dy), (0, frame * size))
    return sheet


def build_state(state, info):
    dest = OUT / state
    if dest.exists():
        shutil.rmtree(dest)
    tex = dest / 'textures/blocks'
    tex.mkdir(parents=True)
    manifest = {'format_version': 2, 'header': {'name': info['name'], 'description': 'Экспериментальная вода из изображений пользователя; VV', 'uuid': info['header'], 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]}, 'modules': [{'type': 'resources', 'uuid': info['module'], 'version': [1, 0, 0]}], 'capabilities': ['pbr']}
    (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for kind, size in [('still', 128), ('flow', 256)]:
        base = f'water_{kind}_grey'
        color = soften_baked_highlights(seamless(square_crop(REFERENCE / info['color'], size)))
        normal = normalize_map(seamless(square_crop(REFERENCE / info['normal'], size)))
        # The vanilla normal/MERS files are TGA. Unique names prevent the
        # engine accidentally resolving a lower-priority vanilla .tga instead
        # of our PNGs. Color keeps the vanilla name so its atlas is overridden.
        normal_name = f'realistic_{state}_{kind}_normal'
        mers_name = f'realistic_{state}_{kind}_mers'
        flipbook(color, 235).save(tex / f'{base}.png', optimize=True)
        flipbook(normal, 255).save(tex / f'{normal_name}.png', optimize=True)
        Image.new('RGBA', (size, size * FRAMES), (0, 0, 36, 0)).save(tex / f'{mers_name}.png', optimize=True)
        descriptor = {'format_version': '1.21.30', 'minecraft:texture_set': {'color': base, 'normal': normal_name, 'metalness_emissive_roughness_subsurface': mers_name}}
        (tex / f'{base}.texture_set.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    water = {'format_version': '1.26.0', 'minecraft:water_settings': {
        'description': {'identifier': 'realistic_water:water'},
        'particle_concentrations': {'chlorophyll': 0.20, 'suspended_sediment': 0.12, 'cdom': 0.20},
        'waves': {'enabled': True, 'depth': info['depth'], 'direction_increment': 65.0, 'frequency': info['frequency'], 'frequency_scaling': 1.2, 'mix': 0.2, 'octaves': info['octaves'], 'pull': 0.3, 'sampleWidth': 0.08, 'shape': 1.5, 'speed': info['speed'], 'speed_scaling': 1.03},
        'caustics': {'enabled': True, 'frame_length': 0.09, 'power': 1, 'scale': 0.6},
        'biome_water_color_contribution': 0.0,
    }}
    (dest / 'water').mkdir()
    (dest / 'water/mobile_water.json').write_text(json.dumps(water, indent=2) + '\n')
    water['minecraft:water_settings']['description']['identifier'] = 'minecraft:default_water'
    (dest / 'water/water.json').write_text(json.dumps(water, indent=2) + '\n')
    # Preserve the previous pack's lighting/fog/sounds for the four supported
    # biome bindings while replacing only their water identifier.
    (dest / 'biomes').mkdir()
    for source in sorted((ROOT / 'realistic-atmosphere/biomes').glob('*.client_biome.json')):
        data = json.loads(source.read_text())
        data['minecraft:client_biome']['components']['minecraft:water_identifier']['water_identifier'] = 'realistic_water:water'
        (dest / 'biomes' / source.name).write_text(json.dumps(data, indent=2) + '\n')
    (dest / 'lighting').mkdir()
    shutil.copyfile(ROOT / 'realistic-atmosphere/lighting/mobile_lighting.json', dest / 'lighting/mobile_lighting.json')


def main():
    for state, info in STATES.items():
        build_state(state, info)
    print('Prepared calm and rough water resources from the supplied references.')


if __name__ == '__main__':
    main()
