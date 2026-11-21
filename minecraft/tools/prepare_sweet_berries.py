#!/usr/bin/env python3
"""Prepare all four sweet-berry-bush stages from the supplied JPG.

Run from the repository root. Requires Pillow, numpy and scipy. The apparent
checkerboard is baked into the JPEG, not transparency; its neutral colours are
removed with an approximate chroma matte. The vanilla item is not changed.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/sweet-berry-reference/growth.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
CROPS = {0: (0, 430, 222, 670), 1: (225, 330, 524, 674),
         2: (525, 240, 883, 680), 3: (884, 175, 1264, 680)}
HEIGHTS = {0: 256, 1: 372, 2: 440, 3: 496}


def prepare_stage(stage):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 848):
            raise ValueError('Expected the supplied 1264x848 JPEG')
        rgb = np.asarray(image.crop(CROPS[stage]), dtype=np.float32)
    # The pale grey/white checker is nearly neutral. Strongly coloured
    # foliage, berries, and dark branches are foreground seeds.
    high, low = rgb.max(axis=2), rgb.min(axis=2)
    chroma = high - low
    seed = ((chroma >= 28) & (low < 200)) | (high < 160)
    if not np.any(seed):
        raise ValueError(f'No foreground for stage {stage}')
    distance, nearest = distance_transform_edt(~seed, return_indices=True)
    nearest_rgb = rgb[nearest[0], nearest[1]]
    nearest_chroma = np.maximum(nearest_rgb.max(axis=2) - nearest_rgb.min(axis=2), 16)
    alpha = np.clip((chroma - 3.0) / np.maximum(nearest_chroma - 3.0, 1), 0, 1)
    alpha = np.where(high < 170, 1, alpha)
    alpha = np.where(seed, 1, alpha)
    alpha = np.where(distance <= 8, alpha, 0)
    # Decontaminate pale checkerboard colours in semi-transparent edge pixels.
    mix = np.clip((alpha - .85) / .15, 0, 1)[..., None]
    color = np.clip(rgb * mix + nearest_rgb * (1 - mix), 0, 255)
    # JPEG can bake a pale fringe into otherwise solid edge pixels. Replace
    # those near-neutral edge colours with nearby strongly coloured foliage;
    # saturated red berries and inner leaf highlights keep their original RGB.
    core = seed & (high < 170) & (chroma > 35)
    if np.any(core):
        core_indices = distance_transform_edt(~core, return_distances=False, return_indices=True)
        core_rgb = rgb[core_indices[0], core_indices[1]]
        edge_distance = distance_transform_edt(alpha > .8)
        strength = (np.clip((low - 100) / 65, 0, 1) *
                    np.clip((3 - edge_distance) / 2, 0, 1))[..., None]
        color = color * (1 - strength) + core_rgb * strength
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    # Remove stray, disconnected pixels or neighbour slivers at crop edges,
    # keeping the translucent border around the largest bush component.
    labels, count = label(alpha >= .38, structure=np.ones((3, 3), dtype=np.uint8))
    if not count:
        raise ValueError(f'No connected bush in stage {stage}')
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    keep = binary_dilation(labels == int(np.argmax(sizes)), structure=np.ones((5, 5)))
    rgba[~keep] = 0
    rgba[rgba[..., 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    # Use a solid-mask bounding box to ignore sparse JPEG noise.
    bounds = plant.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if bounds is None:
        raise ValueError(f'Empty stage {stage}')
    x0, y0, x1, y1 = bounds
    plant = plant.crop((max(0, x0-2), max(0, y0-2),
                        min(plant.width, x1+2), min(plant.height, y1+2)))
    height = HEIGHTS[stage]
    width = max(1, round(plant.width * height / plant.height))
    if width > SIZE:
        # Preserve proportions if a bush is wider than it is tall.
        width, height = SIZE, round(plant.height * SIZE / plant.width)
    plant = plant.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(plant, ((SIZE-width)//2, SIZE-height))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for stage in range(4):
        prepare_stage(stage).save(BLOCKS / f'sweet_berry_bush_stage{stage}.png', optimize=True)
    print('Prepared four sweet berry bush growth stages.')


if __name__ == '__main__':
    main()
