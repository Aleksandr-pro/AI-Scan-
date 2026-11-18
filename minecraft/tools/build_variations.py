#!/usr/bin/env python3
"""Build the Bedrock texture variants from the existing dirt and grass textures.

Requires Pillow. Run from repository root: python minecraft/tools/build_variations.py
The original dirt texture is not modified.
"""
from pathlib import Path
import json
import math
import zipfile
from PIL import Image, ImageChops

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

# Short grass variants are preprocessed, full-colour user-provided textures.
# Keep their alpha and detail intact rather than synthesizing or desaturating
# them. The standard crossed-plane model and engine biome tint still apply.
for variant in range(5):
    img = Image.open(blocks / f'short_grass_variant_{variant}.png')
    if img.size != (size, size) or img.mode != 'RGBA':
        raise ValueError('Short grass variants must be 256x256 RGBA')
    if variant == 0:
        img.save(blocks / 'tallgrass.png', optimize=True)

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

# Vary the masonry inside a shared border so neighbouring variants retain
# the same edge pixels. Keep the horizontal courses oriented horizontally.
stone = Image.open(blocks / 'stone.png').convert('RGB')
inner = Image.new('L', (size, size))
inner.putdata([round(255 * min(1, max(0, min(x, y, size-1-x, size-1-y) / 48)))
               for y in range(size) for x in range(size)])
for i in range(4):
    varied = ImageChops.offset(stone, i * 37, i * 19)
    Image.composite(varied, stone, inner).save(blocks / f'stone_variant_{i}.png', optimize=True)

# Keep brick courses aligned and the edges identical in every variant.
# Vary only the tone in the interior, not brick placement or orientation.
brick = Image.open(blocks / 'brick.png').convert('RGB')
bsize = brick.width
brick_mask = Image.new('L', (bsize, bsize))
brick_mask.putdata([round(255 * min(1, max(0, min(x, y, bsize-1-x, bsize-1-y) / 48)))
                    for y in range(bsize) for x in range(bsize)])
for i, factor in enumerate((1.0, 0.95, 1.05, 0.98)):
    tinted = brick.point(lambda value: min(255, round(value * factor)))
    Image.composite(tinted, brick, brick_mask).save(blocks / f'brick_variant_{i}.png', optimize=True)

# Oak planks retain their horizontal joints and identical tile boundaries;
# only the interior tone changes, rather than rotating the wood grain.
planks = Image.open(blocks / 'planks_oak.png').convert('RGB')
if planks.size != brick.size:
    raise ValueError('Oak plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = planks.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, planks, brick_mask).save(blocks / f'planks_oak_variant_{i}.png', optimize=True)

# Spruce uses the same edge-safe approach; don't rotate the plank courses.
spruce = Image.open(blocks / 'planks_spruce.png').convert('RGB')
if spruce.size != brick.size:
    raise ValueError('Spruce plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = spruce.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, spruce, brick_mask).save(blocks / f'planks_spruce_variant_{i}.png', optimize=True)

# Birch also retains the same direction and common borders across variants.
birch = Image.open(blocks / 'planks_birch.png').convert('RGB')
if birch.size != brick.size:
    raise ValueError('Birch plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = birch.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, birch, brick_mask).save(blocks / f'planks_birch_variant_{i}.png', optimize=True)

# Jungle plank variants preserve the grain orientation and shared tile edges.
jungle = Image.open(blocks / 'planks_jungle.png').convert('RGB')
if jungle.size != brick.size:
    raise ValueError('Jungle plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = jungle.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, jungle, brick_mask).save(blocks / f'planks_jungle_variant_{i}.png', optimize=True)

# Acacia keeps its horizontal grain and uses the same border across variants.
acacia = Image.open(blocks / 'planks_acacia.png').convert('RGB')
if acacia.size != brick.size:
    raise ValueError('Acacia plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = acacia.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, acacia, brick_mask).save(blocks / f'planks_acacia_variant_{i}.png', optimize=True)

# Mangrove variants keep the same horizontal grain and shared border.
mangrove = Image.open(blocks / 'mangrove_planks.png').convert('RGB')
if mangrove.size != brick.size:
    raise ValueError('Mangrove plank and brick source textures must both be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = mangrove.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, mangrove, brick_mask).save(blocks / f'mangrove_planks_variant_{i}.png', optimize=True)

# Dark oak and cherry retain orientation and matching tile boundaries.
for material in ('planks_big_oak', 'cherry_planks'):
    plank = Image.open(blocks / f'{material}.png').convert('RGB')
    if plank.size != brick.size:
        raise ValueError(f'{material} texture must be 512x512')
    for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
        shaded = plank.point(lambda value: min(255, round(value * factor)))
        Image.composite(shaded, plank, brick_mask).save(blocks / f'{material}_variant_{i}.png', optimize=True)

# Diamond ore: preserve the photographic shapes and shared borders while
# introducing modest tonal differences, with the original as a fallback.
ore = Image.open(blocks / 'diamond_ore.png').convert('RGB')
if ore.size != brick.size:
    raise ValueError('Diamond ore source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = ore.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, ore, brick_mask).save(blocks / f'diamond_ore_variant_{i}.png', optimize=True)

# Iron ore uses the user-supplied texture and edge-matched tonal variants.
iron_ore = Image.open(blocks / 'iron_ore.png').convert('RGB')
if iron_ore.size != brick.size:
    raise ValueError('Iron ore source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = iron_ore.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, iron_ore, brick_mask).save(blocks / f'iron_ore_variant_{i}.png', optimize=True)

# Copper ore: keep shared borders while varying the interior tone slightly.
copper_ore = Image.open(blocks / 'copper_ore.png').convert('RGB')
if copper_ore.size != brick.size:
    raise ValueError('Copper ore source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = copper_ore.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, copper_ore, brick_mask).save(blocks / f'copper_ore_variant_{i}.png', optimize=True)

# Gravel variants keep the source's stone arrangement and shared borders.
gravel = Image.open(blocks / 'gravel.png').convert('RGB')
if gravel.size != brick.size:
    raise ValueError('Gravel source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = gravel.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, gravel, brick_mask).save(blocks / f'gravel_variant_{i}.png', optimize=True)

# Soul sand retains the reference's face pattern and common tile borders.
soul_sand = Image.open(blocks / 'soul_sand.png').convert('RGB')
if soul_sand.size != brick.size:
    raise ValueError('Soul sand source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = soul_sand.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, soul_sand, brick_mask).save(blocks / f'soul_sand_variant_{i}.png', optimize=True)

# Gold block's bevel is intentional: keep it, and vary only the interior tone.
gold_block = Image.open(blocks / 'gold_block.png').convert('RGB')
if gold_block.size != brick.size:
    raise ValueError('Gold block source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = gold_block.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, gold_block, brick_mask).save(blocks / f'gold_block_variant_{i}.png', optimize=True)

# Separate sand sides and top retain a common boundary within each variant set.
for material in ('sand', 'realistic_sand_top'):
    sand = Image.open(blocks / f'{material}.png').convert('RGB')
    if sand.size != brick.size:
        raise ValueError(f'{material} source texture must be 512x512')
    for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
        shaded = sand.point(lambda value: min(255, round(value * factor)))
        Image.composite(shaded, sand, brick_mask).save(blocks / f'{material}_variant_{i}.png', optimize=True)

# Separate snow top and side textures, with matching edges between variants.
for material in ('snow', 'realistic_snow_top'):
    snow = Image.open(blocks / f'{material}.png').convert('RGB')
    if snow.size != brick.size:
        raise ValueError(f'{material} source texture must be 512x512')
    for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
        shaded = snow.point(lambda value: min(255, round(value * factor)))
        Image.composite(shaded, snow, brick_mask).save(blocks / f'{material}_variant_{i}.png', optimize=True)

# Amethyst block retains crystal detail and a shared edge across variants.
amethyst = Image.open(blocks / 'amethyst_block.png').convert('RGB')
if amethyst.size != brick.size:
    raise ValueError('Amethyst block source texture must be 512x512')
for i, factor in enumerate((1.0, 0.97, 1.03, 0.985)):
    shaded = amethyst.point(lambda value: min(255, round(value * factor)))
    Image.composite(shaded, amethyst, brick_mask).save(blocks / f'amethyst_block_variant_{i}.png', optimize=True)

# Preserve all 17 vanilla grass-top entries (biome/state indices) while assigning
# the same position-selected set at each index. Weights are explicit.
tops = [{'path': f'textures/blocks/grass_top_variant_{i}', 'weight': 1} for i in range(4)]
sides = [{'path': f'textures/blocks/grass_side_variant_{i:02}', 'weight': 1} for i in range(16)]
plants = [{'path': f'textures/blocks/short_grass_variant_{i}', 'weight': 1} for i in range(5)]
terrain = {'resource_pack_name': 'vanilla', 'texture_name': 'atlas.terrain', 'padding': 8, 'num_mip_levels': 4,
           'texture_data': {
               'grass_top': {'textures': [{'variations': tops} for _ in range(17)]},
               'grass_side': {'textures': [{'overlay_color': '#df6827', 'variations': sides}]},
               'short_grass': {'textures': {'variations': plants}},
               # Keep the legacy stonebrick indexed atlas intact: its first
               # vanilla path is also textures/blocks/stonebrick.
               'stone_bricks': {'textures': 'textures/blocks/stonebrick'},
               # Two halves of the same plant image; never randomize separately.
               # Vanilla legacy double_plant indices also reference these paths.
               'tall_grass_top': {'textures': 'textures/blocks/double_plant_grass_top'},
               'tall_grass_bottom': {'textures': 'textures/blocks/double_plant_grass_bottom'},
               # Five preprocessed user-supplied dirt panels share their borders;
               # keep dirt.png untouched for grass/path and legacy texture users.
               'flattened_dirt': {'textures': {'variations': [
                   {'path': f'textures/blocks/dirt_variant_{i}', 'weight': 1} for i in range(5)]}},
               # Keep Bedrock's own hay block face assignment and axis rotation.
               'hayblock_side': {'textures': 'textures/blocks/hay_block_side'},
               'hayblock_top': {'textures': 'textures/blocks/hay_block_top'},
               # Use one shared tile per block, retaining periodic borders.
               **{name: {'textures': f'textures/blocks/{name}'}
                  for name in ('redstone_block', 'diamond_block', 'wool_colored_white')},
               'obsidian': {'textures': 'textures/blocks/obsidian'},
               **{f'real_obsidian_{face}': {'textures': f'textures/blocks/obsidian_{face}'}
                  for face in ('north', 'east', 'south', 'west', 'down')},
               'amethyst_block': {'textures': {'variations': [
                   {'path': f'textures/blocks/amethyst_block_variant_{i}', 'weight': 1} for i in range(4)]}},
               'snow': {'textures': {'variations': [
                   {'path': f'textures/blocks/snow_variant_{i}', 'weight': 1} for i in range(4)]}},
               'realistic_snow_top': {'textures': {'variations': [
                   {'path': f'textures/blocks/realistic_snow_top_variant_{i}', 'weight': 1} for i in range(4)]}},
               'flattened_sand': {'textures': {'variations': [
                   {'path': f'textures/blocks/sand_variant_{i}', 'weight': 1} for i in range(4)]}},
               'realistic_sand_top': {'textures': {'variations': [
                   {'path': f'textures/blocks/realistic_sand_top_variant_{i}', 'weight': 1} for i in range(4)]}},
               'gold_block': {'textures': {'variations': [
                   {'path': f'textures/blocks/gold_block_variant_{i}', 'weight': 1} for i in range(4)]}},
               'soul_sand': {'textures': {'variations': [
                   {'path': f'textures/blocks/soul_sand_variant_{i}', 'weight': 1} for i in range(4)]}},
               'gravel': {'textures': {'variations': [
                   {'path': f'textures/blocks/gravel_variant_{i}', 'weight': 1} for i in range(4)]}},
               'copper_ore': {'textures': {'variations': [
                   {'path': f'textures/blocks/copper_ore_variant_{i}', 'weight': 1} for i in range(4)]}},
               'iron_ore': {'textures': {'variations': [
                   {'path': f'textures/blocks/iron_ore_variant_{i}', 'weight': 1} for i in range(4)]}},
               'diamond_ore': {'textures': {'variations': [
                   {'path': f'textures/blocks/diamond_ore_variant_{i}', 'weight': 1} for i in range(4)]}},
               'dark_oak_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_big_oak_variant_{i}', 'weight': 1} for i in range(4)]}},
               'cherry_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/cherry_planks_variant_{i}', 'weight': 1} for i in range(4)]}},
               'mangrove_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/mangrove_planks_variant_{i}', 'weight': 1} for i in range(4)]}},
               'acacia_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_acacia_variant_{i}', 'weight': 1} for i in range(4)]}},
               'jungle_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_jungle_variant_{i}', 'weight': 1} for i in range(4)]}},
               'birch_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_birch_variant_{i}', 'weight': 1} for i in range(4)]}},
               'spruce_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_spruce_variant_{i}', 'weight': 1} for i in range(4)]}},
               'oak_planks': {'textures': {'variations': [
                   {'path': f'textures/blocks/planks_oak_variant_{i}', 'weight': 1} for i in range(4)]}},
               'brick': {'textures': {'variations': [
                   {'path': f'textures/blocks/brick_variant_{i}', 'weight': 1} for i in range(4)]}},
               'flattened_stone': {'textures': {'variations': [
                   {'path': f'textures/blocks/stone_variant_{i}', 'weight': 1} for i in range(4)]}},
               'gray_concrete': {'textures': {'variations': [
                   {'path': f'textures/blocks/concrete_gray_variant_{i}', 'weight': 1} for i in range(4)]}},
               'grass_path_top': {'textures': [{'variations': [
                   {'path': f'textures/blocks/grass_path_top_variant_{i}', 'weight': 1} for i in range(4)]}]},
               'grass_path_side': {'textures': [{'variations': [
                   {'path': f'textures/blocks/grass_path_side_variant_{i}', 'weight': 1} for i in range(4)]}]},
           }}
# Reuse base PNGs only when a generated variant_0 is byte-for-byte identical.
# Limit this to explicitly referenced variation paths: vanilla and other pack
# assets may load their original filenames implicitly. Source files are kept.
omitted = set()
def reuse_identical_variants(value):
    if isinstance(value, dict):
        if 'variations' in value:
            for variant in value['variations']:
                path = variant.get('path', '')
                if not path.endswith('_variant_0'):
                    continue
                original = root / (path + '.png')
                base_path = path.removesuffix('_variant_0')
                base = root / (base_path + '.png')
                if original.is_file() and base.is_file() and original.read_bytes() == base.read_bytes():
                    # Never remove a file that another pack JSON refers to.
                    others = (p for p in root.rglob('*.json') if p.name != 'terrain_texture.json')
                    if any(path in p.read_text(encoding='utf-8') for p in others):
                        continue
                    variant['path'] = base_path
                    omitted.add(original.relative_to(root))
        for child in value.values():
            reuse_identical_variants(child)
    elif isinstance(value, list):
        for child in value:
            reuse_identical_variants(child)

reuse_identical_variants(terrain)
# If another atlas entry still names a candidate, retain the file.
serialized = json.dumps(terrain, indent=2) + '\n'
omitted = {p for p in omitted if str(p.with_suffix('')) not in serialized}
(root / 'textures/terrain_texture.json').write_text(serialized, encoding='utf-8')
with zipfile.ZipFile('minecraft/realistic-dirt.mcpack', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.relative_to(root) not in omitted:
            archive.write(path, path.relative_to(root))
print(f'Reused {len(omitted)} identical variation files; source textures retained.')
