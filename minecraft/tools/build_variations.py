#!/usr/bin/env python3
"""Build the Bedrock texture variants from the existing dirt and grass textures.

Requires Pillow. Run from repository root: python minecraft/tools/build_variations.py
The original dirt texture is not modified.
"""
from pathlib import Path
import json
import math
import random
import zipfile
from PIL import Image, ImageChops, ImageDraw

root = Path('minecraft/realistic-dirt')
blocks = root / 'textures/blocks'
size = 256
base_grass = Image.open(blocks / 'grass_top.png').convert('L').resize((size, size), Image.Resampling.LANCZOS)
dirt = Image.open(blocks / 'dirt.png').convert('RGB').resize((size, size), Image.Resampling.LANCZOS)

# Quarter turns and their reflections preserve the already blended tile edges.
for i in range(4):
    top = base_grass.rotate(90 * i).convert('RGB')
    top.save(blocks / f'grass_top_variant_{i}.png', optimize=True)

# Keep the soil identical for all sides and adjust only the periodic grass edge.
# The alpha channel is Bedrock's biome tint mask for grass_side TGA.
for i in range(16):
    image = Image.new('RGBA', (size, size))
    pix, soil, grass = image.load(), dirt.load(), base_grass.load()
    phase = i * math.pi / 8
    for y in range(size):
        for x in range(size):
            t = 2 * math.pi * x / size
            edge = 37 + 4 * math.sin(3*t + phase) + 2.5 * math.sin(9*t - phase) + math.sin(19*t + phase)
            blend = max(0.0, min(1.0, (edge-y)/3.5 + 0.5))
            g = grass[x, y]
            d = soil[x, y]
            pix[x, y] = tuple(round(d[k]*(1-blend) + g*blend) for k in range(3)) + (round(blend*255),)
    image.save(blocks / f'grass_side_variant_{i:02}.tga')

# Vanilla short grass already renders as crossed planes: provide translucent blades
# and variations without changing block geometry or adding costly world entities.
for variant in range(4):
    rng = random.Random(5917 + variant)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for n in range(60):
        x = rng.randint(38, 218)
        bottom = rng.randint(222, 255)
        tipx = max(1, min(254, x + rng.randint(-75, 75)))
        tipy = rng.randint(30, 185)
        width = rng.randint(2, 7)
        shade = rng.randint(95, 210)
        draw.polygon([(x-width, bottom), (tipx, tipy), (x+width, bottom)], fill=(shade, shade, shade, 255))
    img.save(blocks / f'short_grass_variant_{variant}.png', optimize=True)

# Path top uses the supplied ground photograph; the side uses the supplied
# grassy-earth photograph, blended into the existing dirt at the bottom.
path_top = Image.open(blocks / 'grass_path_top.png').convert('RGB')
path_side = Image.open(blocks / 'grass_path_side_source.png').convert('RGB')
for i in range(4):
    path_top.rotate(90 * i).save(blocks / f'grass_path_top_variant_{i}.png', optimize=True)
    shifted = ImageChops.offset(path_side, i * size // 4, 0)
    mask = Image.new('L', (size, size))
    mask.putdata([round(255 * max(0, min(1, (y - 130) / 65))) for y in range(size) for x in range(size)])
    Image.composite(dirt, shifted, mask).save(blocks / f'grass_path_side_variant_{i}.png', optimize=True)
# The fallback filename also works when variations are not supported.
Image.open(blocks / 'grass_path_side_variant_0.png').save(blocks / 'grass_path_side.png', optimize=True)

# Four rotations of the supplied gray concrete photograph. The unmodified
# concrete_gray.png is also used by older indexed concrete atlas entries.
concrete = Image.open(blocks / 'concrete_gray.png').convert('RGB')
for i in range(4):
    concrete.rotate(90 * i).save(blocks / f'concrete_gray_variant_{i}.png', optimize=True)

# Preserve all 17 vanilla grass-top entries (biome/state indices) while assigning
# the same position-selected set at each index. Weights are explicit.
tops = [{'path': f'textures/blocks/grass_top_variant_{i}', 'weight': 1} for i in range(4)]
sides = [{'path': f'textures/blocks/grass_side_variant_{i:02}', 'weight': 1} for i in range(16)]
plants = [{'path': f'textures/blocks/short_grass_variant_{i}', 'weight': 1} for i in range(4)]
terrain = {'resource_pack_name': 'vanilla', 'texture_name': 'atlas.terrain', 'padding': 8, 'num_mip_levels': 4,
           'texture_data': {
               'grass_top': {'textures': [{'variations': tops} for _ in range(17)]},
               'grass_side': {'textures': [{'overlay_color': '#df6827', 'variations': sides}]},
               'short_grass': {'textures': {'variations': plants}},
               'gray_concrete': {'textures': {'variations': [
                   {'path': f'textures/blocks/concrete_gray_variant_{i}', 'weight': 1} for i in range(4)]}},
               'grass_path_top': {'textures': [{'variations': [
                   {'path': f'textures/blocks/grass_path_top_variant_{i}', 'weight': 1} for i in range(4)]}]},
               'grass_path_side': {'textures': [{'variations': [
                   {'path': f'textures/blocks/grass_path_side_variant_{i}', 'weight': 1} for i in range(4)]}]},
           }}
(root / 'textures/terrain_texture.json').write_text(json.dumps(terrain, indent=2) + '\n', encoding='utf-8')
with zipfile.ZipFile('minecraft/realistic-dirt.mcpack', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(root))
