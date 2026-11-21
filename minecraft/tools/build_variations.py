#!/usr/bin/env python3
"""Build the Bedrock texture pack and its generated variants.

Requires Pillow. Run from repository root: python minecraft/tools/build_variations.py
Grass tops and sides are prepared assets and are never regenerated here.
"""
from pathlib import Path
import json
import zipfile
from PIL import Image, ImageChops

root = Path('minecraft/realistic-dirt')
blocks = root / 'textures/blocks'
size = 256
dirt = Image.open(blocks / 'dirt.png').convert('RGB').resize((size, size), Image.Resampling.LANCZOS)

# Keep the four user-supplied top photographs in full colour. Do not derive
# them from grass_top.png or alter the existing grass-side tint-mask textures.
for filename in ['grass_top.png'] + [f'grass_top_variant_{i}.png' for i in range(1, 4)]:
    with Image.open(blocks / filename) as top:
        if top.mode != 'RGB' or top.size != (512, 512):
            raise ValueError('Grass top variants must be 512x512 RGB')
for i in range(16):
    with Image.open(blocks / f'grass_side_variant_{i:02}.tga') as side:
        if side.mode != 'RGBA' or side.size != (size, size):
            raise ValueError('Prepared grass side variants must be 256x256 RGBA')

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

# Sand uses one prepared, tileable user photograph on every face. Keeping
# just the base texture avoids duplicate files and shade differences by face.
with Image.open(blocks / 'sand.png') as sand:
    if sand.mode != 'RGB' or sand.size != (512, 512):
        raise ValueError('Sand texture must be 512x512 RGB')

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
tops = [{'path': 'textures/blocks/grass_top', 'weight': 1}] + [
    {'path': f'textures/blocks/grass_top_variant_{i}', 'weight': 1} for i in range(1, 4)]
sides = [{'path': f'textures/blocks/grass_side_variant_{i:02}', 'weight': 1} for i in range(16)]
# Variant zero is byte-identical to tallgrass.png, the vanilla fallback. Use
# one archive copy while retaining both prepared source files for rebuilding.
if (blocks / 'short_grass_variant_0.png').read_bytes() != (blocks / 'tallgrass.png').read_bytes():
    raise ValueError('Short grass alias must be byte-identical to tallgrass')
plants = [{'path': 'textures/blocks/tallgrass', 'weight': 1}] + [
    {'path': f'textures/blocks/short_grass_variant_{i}', 'weight': 1} for i in range(1, 5)]
terrain = {'resource_pack_name': 'vanilla', 'texture_name': 'atlas.terrain', 'padding': 8, 'num_mip_levels': 4,
           'texture_data': {
               # A separate atlas key changes only the full glass block, not
               # the vanilla glass texture shared by uncoloured glass panes.
               'realistic_clear_glass': {'textures': 'textures/blocks/realistic_clear_glass'},
               # Standard ground leaf litter; carried item remains vanilla.
               'leaf_litter': {'textures': 'textures/blocks/leaf_litter'},
               # Preserve vanilla cactus faces, reusing the single end image.
               'cactus_side': {'textures': 'textures/blocks/cactus_side'},
               'cactus_top': {'textures': 'textures/blocks/cactus_top'},
               'cactus_bottom': {'textures': 'textures/blocks/cactus_top'},
               'grass_top': {'textures': [{'variations': tops} for _ in range(17)]},
               # Vanilla's held/inventory top normally points at grass_carried;
               # reuse the new first top without keeping a duplicate image.
               'grass_carried_top': {'textures': 'textures/blocks/grass_top'},
               'grass_side': {'textures': [{'overlay_color': '#df6827', 'variations': sides}]},
               'short_grass': {'textures': {'variations': plants}},
               # Vanilla one-block fern; large fern keeps its own textures.
               'fern': {'textures': 'textures/blocks/fern'},
               # Bedrock's vanilla farmland texture indices are wet, then dry.
               # Moist is a position-selected wet-slot variant, not a new
               # hydration state: resource packs cannot change that mapping.
               'farmland': {'textures': [
                   {'variations': [
                       {'path': 'textures/blocks/farmland_wet', 'weight': 1},
                       {'path': 'textures/blocks/farmland_moist', 'weight': 1},
                   ]},
                   'textures/blocks/farmland_dry',
               ]},
               'farmland_side': {'textures': 'textures/blocks/farmland_side'},
               # Vanilla log/log_side indexed arrays retain their layout;
               # their oak entries use these same paths.
               'oak_log_top': {'textures': 'textures/blocks/log_oak_top'},
               'oak_log_side': {'textures': 'textures/blocks/log_oak'},
               'spruce_log_top': {'textures': 'textures/blocks/log_spruce_top'},
               'spruce_log_side': {'textures': 'textures/blocks/log_spruce'},
               'birch_log_top': {'textures': 'textures/blocks/log_birch_top'},
               'birch_log_side': {'textures': 'textures/blocks/log_birch'},
               'jungle_log_top': {'textures': 'textures/blocks/log_jungle_top'},
               'jungle_log_side': {'textures': 'textures/blocks/log_jungle'},
               'acacia_log_top': {'textures': 'textures/blocks/log_acacia_top'},
               'acacia_log_side': {'textures': 'textures/blocks/log_acacia'},
               'dark_oak_log_top': {'textures': 'textures/blocks/log_big_oak_top'},
               'dark_oak_log_side': {'textures': 'textures/blocks/log_big_oak'},
               'mangrove_log_top': {'textures': 'textures/blocks/mangrove_log_top'},
               'mangrove_log_side': {'textures': 'textures/blocks/mangrove_log_side'},
               'cherry_log_top': {'textures': 'textures/blocks/cherry_log_top'},
               'cherry_log_side': {'textures': 'textures/blocks/cherry_log_side'},
               # Vanilla bamboo stem is an opaque cube-face texture, not a
               # cutout sprite; leaves and the sapling keep their vanilla paths.
               'bamboo_stem': {'textures': 'textures/blocks/bamboo_stem'},
               'bamboo_block': {'textures': 'textures/blocks/bamboo_block'},
               'bamboo_block_top': {'textures': 'textures/blocks/bamboo_block_top'},
               'stripped_bamboo_block': {'textures': 'textures/blocks/stripped_bamboo_block'},
               'stripped_bamboo_block_top': {'textures': 'textures/blocks/stripped_bamboo_block_top'},
               'ladder': {'textures': 'textures/blocks/ladder'},
               # Vanilla lantern uses a 16x16 UV layout in a three-frame strip.
               'lantern': {'textures': 'textures/blocks/lantern'},
               # Bedrock's sea-lantern flipbook uses five square frames.
               'sea_lantern': {'textures': 'textures/blocks/sea_lantern'},
               'glowstone': {'textures': 'textures/blocks/glowstone'},
               # The brick path is also used by the vanilla indexed prismarine
               # atlas and by slabs/stairs; rough and dark prismarine stay vanilla.
               'prismarine_bricks': {'textures': 'textures/blocks/prismarine_bricks'},
               'prismarine_brick_slab': {'textures': 'textures/blocks/prismarine_bricks'},
               'iron_block': {'textures': 'textures/blocks/iron_block'},
               # Ordinary nether brick is also used by fences and stairs; its
               # vanilla slab and wall entries refer to the same image.
               'nether_brick': {'textures': 'textures/blocks/nether_brick'},
               'nether_brick_slab': {'textures': 'textures/blocks/nether_brick'},
               'nether_brick_wall': {'textures': 'textures/blocks/nether_brick'},
               # The legacy indexed stone atlas also uses this vanilla path.
               'diorite': {'textures': 'textures/blocks/stone_diorite'},
               'polished_diorite': {'textures': 'textures/blocks/stone_diorite_smooth'},
               # Four distinct user-supplied images, with shared tile borders.
               # The first also serves as the vanilla filename fallback.
               'netherrack': {'textures': {'variations': [
                   {'path': 'textures/blocks/netherrack', 'weight': 1},
                   *[{'path': f'textures/blocks/netherrack_variant_{i}', 'weight': 1}
                     for i in range(1, 4)]]}},
               # Keep the fancy/opaque indices in the vanilla order. Legacy
               # indexed leaves also use these same two oak-specific filenames.
               'oak_leaves': {'textures': ['textures/blocks/leaves_oak',
                                           'textures/blocks/leaves_oak_opaque']},
               # Keep the legacy stonebrick indexed atlas intact: its first
               # vanilla path is also textures/blocks/stonebrick.
               'stone_bricks': {'textures': 'textures/blocks/stonebrick'},
               # Preserve vanilla paths; related slabs, walls, stairs and
               # legacy indexed entries can reference the same two images.
               'cobblestone': {'textures': 'textures/blocks/cobblestone'},
               'cobblestone_mossy': {'textures': 'textures/blocks/cobblestone_mossy'},
               # Explicit modern atlas entries; matching vanilla file paths
               # also support legacy indexed entries and related shapes.
               'clay': {'textures': 'textures/blocks/clay'},
               'flattened_sandstone': {'textures': 'textures/blocks/sandstone_normal'},
               # Normal and waxed unoxidized grates share this vanilla path.
               'copper_grate': {'textures': 'textures/blocks/copper_grate'},
               'flattened_quartz_block_top': {'textures': 'textures/blocks/quartz_block_top'},
               'flattened_quartz_block_side': {'textures': 'textures/blocks/quartz_block_side'},
               'smooth_quartz': {'textures': 'textures/blocks/quartz_block_bottom'},
               'quartz_bricks': {'textures': 'textures/blocks/quartz_bricks'},
               'chiseled_quartz_block_top': {'textures': 'textures/blocks/quartz_block_chiseled'},
               'chiseled_quartz_block_side': {'textures': 'textures/blocks/quartz_block_chiseled'},
               'quartz_pillar_top': {'textures': 'textures/blocks/quartz_block_top'},
               'quartz_pillar_side': {'textures': 'textures/blocks/quartz_block_lines'},
               # Four two-block plants. Bedrock may choose the upper and lower
               # variants independently; prepared assets share a narrow join.
               # Vanilla legacy double_plant indices fall back to base paths.
               **{f'tall_grass_{part}': {'textures': {'variations': [
                   {'path': f'textures/blocks/double_plant_grass_{part}' + (f'_variant_{i}' if i else ''), 'weight': 1}
                   for i in range(4)]}} for part in ('top', 'bottom')},
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
               'flattened_sand': {'textures': 'textures/blocks/sand'},
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
# Private inventory names avoid changing the trapped chest's shared vanilla faces.
for face in ('front', 'side', 'top'):
    terrain['texture_data']['photo_chest_' + face] = {
        'textures': 'textures/blocks/photo_chest_' + face
    }

# Assign all four distinct side photographs and the top to the crafting table.
for face in ('north', 'east', 'south', 'west', 'top'):
    terrain['texture_data']['photo_crafting_table_' + face] = {
        'textures': 'textures/blocks/photo_crafting_table_' + face
    }

# Preserve all vanilla legacy quartz indices while aliasing the two caps
# that are byte-identical to their corresponding existing photographs.
for alias, canonical in (('quartz_block_chiseled_top','quartz_block_chiseled'),
                         ('quartz_block_lines_top','quartz_block_top')):
    if (blocks / (alias+'.png')).read_bytes() != (blocks / (canonical+'.png')).read_bytes():
        raise ValueError(f'Quartz alias is no longer identical: {alias}')
quartz_caps = ['textures/blocks/'+n for n in
               ('quartz_block_top','quartz_block_chiseled','quartz_block_top','quartz_block_bottom')]
for key in ('quartz_block_top','quartz_block_bottom'):
    terrain['texture_data'][key] = {'textures': quartz_caps}

# Furnace-only names avoid changing vanilla textures shared with dispensers
# and droppers. blocks.json keeps vanilla's respective lit/unlit face mapping.
for part in ('body', 'front_on', 'front_off'):
    key = 'photo_furnace_' + part
    terrain['texture_data'][key] = {'textures': 'textures/blocks/' + key}

# Four prepared end-stone photos with a common, periodic tile boundary.
terrain['texture_data']['end_stone'] = {'textures': {'variations': [
    {'path': 'textures/blocks/end_stone' + (f'_variant_{i}' if i else ''), 'weight': 1}
    for i in range(4)
]}}

# Three transparent photographic overlays on the ordinary glow-lichen block.
terrain['texture_data']['glow_lichen'] = {'textures': {'variations': [
    {'path': 'textures/blocks/glow_lichen' + (f'_variant_{i}' if i else ''), 'weight': 1}
    for i in range(3)
]}}

# Four photographic leaf surfaces for each vanilla dripleaf model. Stems,
# sides and model UVs remain independent; no custom plant geometry is added.
for name in ('big_dripleaf_top', 'small_dripleaf_top'):
    terrain['texture_data'][name] = {'textures': {'variations': [
        {'path': 'textures/blocks/' + name + (f'_variant_{i}' if i else ''), 'weight': 1}
        for i in range(4)
    ]}}

# Ordinary moss block and carpet share the same vanilla atlas entry. All
# four photographic tiles share matching borders. Lily pad uses its own
# six full-colour textures; override vanilla's green #208030 static tint.
terrain['texture_data']['moss_block'] = {'textures': {'variations': [
    {'path': 'textures/blocks/moss_block' + (f'_variant_{i}' if i else ''), 'weight': 1}
    for i in range(4)
]}}
terrain['texture_data']['waterlily'] = {'textures': [{
    'tint_color': '#ffffff',
    'variations': [
        {'path': 'textures/blocks/waterlily' + (f'_variant_{i}' if i else ''), 'weight': 1}
        for i in range(6)
    ]
}]}

# Six position-selected ordinary-vine textures; individual blocks are not
# guaranteed to choose matching strands when stacked vertically.
terrain['texture_data']['vine'] = {'textures': {'variations': [
    {'path': 'textures/blocks/vine' + (f'_variant_{i}' if i else ''), 'weight': 1}
    for i in range(6)
]}}

# Two supplied flowers have no exact vanilla counterpart. Offer the violet
# as an allium variant and the buttercup as a dandelion variant where the
# engine supports terrain variations. Legacy red_flower remains unchanged.
flower_variants = {
    'allium': ('flower_allium', 'photo_flower_violet'),
    'dandelion': ('flower_dandelion', 'photo_flower_buttercup'),
    'yellow_flower': ('flower_dandelion', 'photo_flower_buttercup'),
}
for key, names in flower_variants.items():
    terrain['texture_data'][key] = {'textures': {'variations': [
        {'path': 'textures/blocks/' + name, 'weight': 1} for name in names
    ]}}

# Reuse base PNGs only when a generated variant_0 is byte-for-byte identical.
# Limit this to explicitly referenced variation paths: vanilla and other pack
# assets may load their original filenames implicitly. Source files are kept.
# These are strictly build inputs or an exact duplicate, not runtime paths.
# Check the atlas and other JSON before excluding either one from the archive.
extra_omissions = {
    Path('textures/blocks/short_grass_variant_0.png'),
    Path('textures/blocks/grass_path_side_source.png'),
    Path('textures/blocks/quartz_block_chiseled_top.png'),
    Path('textures/blocks/quartz_block_lines_top.png'),
}
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
for path in extra_omissions:
    ref = path.with_suffix('').as_posix()
    if ref in serialized or any(ref in p.read_text(encoding='utf-8') for p in root.rglob('*.json') if p.name != 'terrain_texture.json'):
        raise ValueError(f'Cannot omit a referenced build input: {ref}')
    if not (root / path).is_file():
        raise ValueError(f'Missing build input: {path}')
omitted.update(extra_omissions)
(root / 'textures/terrain_texture.json').write_text(serialized, encoding='utf-8')
with zipfile.ZipFile('minecraft/realistic-dirt.mcpack', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.relative_to(root) not in omitted:
            archive.write(path, path.relative_to(root))
print(f'Omitted {len(omitted)} redundant or build-only files; source textures retained.')
