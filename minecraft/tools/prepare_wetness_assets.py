#!/usr/bin/env python3
"""Derive small wet block textures from the existing pack; requires Pillow."""
import json
from pathlib import Path
from PIL import Image, ImageEnhance

ROOT = Path('minecraft')
SRC = ROOT / 'realistic-dirt/textures/blocks'
OUT = ROOT / 'rain-wetness/resources/textures/blocks'


def darker(image, factor):
    return ImageEnhance.Brightness(image.convert('RGB')).enhance(factor)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dirt = Image.open(SRC / 'dirt.png').convert('RGB')
    top = Image.open(SRC / 'grass_top.png').convert('RGB')
    stone = Image.open(SRC / 'stone.png').convert('RGB')
    overlay = Image.open(SRC / 'grass_side.tga').convert('RGBA')
    # The original grass-side image is a grayscale alpha overlay. Bake a
    # representative green tint into it over the existing dirt base; the top
    # continues to use Bedrock's biome grass tint at render time.
    rgb = overlay.convert('RGB')
    r, g, b = rgb.split()
    tint = Image.merge('RGB', (r.point(lambda x: int(x * .46)), g.point(lambda x: int(x * .69)), b.point(lambda x: int(x * .29))))
    side = Image.composite(tint, dirt, overlay.getchannel('A'))
    images = {
        'rainwet_dirt': darker(dirt, .76),
        'rainwet_stone': darker(stone, .78),
        'rainwet_grass_top': darker(top, .78),
        'rainwet_grass_side': darker(side, .78),
    }
    for name, image in images.items():
        # Bound mobile atlas cost; wet blocks share one texture per face.
        image.resize((256, 256), Image.Resampling.LANCZOS).save(OUT / f'{name}.png', optimize=True)
        descriptor = {'format_version': '1.21.30', 'minecraft:texture_set': {
            'color': name, 'metalness_emissive_roughness_subsurface': [0, 0, 90, 0]}}
        (OUT / f'{name}.texture_set.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    atlas = {'resource_pack_name': 'rain_wetness', 'texture_name': 'atlas.terrain', 'padding': 8, 'num_mip_levels': 4,
             'texture_data': {name: {'textures': f'textures/blocks/{name}'} for name in images}}
    (OUT.parent / 'terrain_texture.json').write_text(json.dumps(atlas, indent=2) + '\n')


if __name__ == '__main__':
    main()
