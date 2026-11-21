#!/usr/bin/env python3
"""Prepare four beetroot crop stages from the supplied growth JPG.

Run from the repository root. Requires Pillow, numpy and scipy. The checker is
baked into the JPEG. Plants 1, 3, 4 and 6 map to Bedrock's four crop textures;
the beetroot item, game rules and geometry are left unchanged.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/beetroot-reference/growth.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
CROPS = {0: (0, 565, 112, 680), 1: (260, 475, 462, 685),
         2: (455, 415, 690, 686), 3: (940, 285, 1264, 695)}
# Comparable to the 4, 5, 8 and 10 pixel visible vanilla crop heights.
HEIGHTS = {0: 128, 1: 160, 2: 256, 3: 320}


def prepare_stage(stage):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 843):
            raise ValueError('Expected the supplied 1264x843 JPEG')
        rgb = np.asarray(image.crop(CROPS[stage]), dtype=np.float32)
    # Checker squares are near neutral grey/white, while leaves and red stems
    # have strong colour. Use nearby object colours for the antialiased edges.
    high, low = rgb.max(axis=2), rgb.min(axis=2)
    chroma = high - low
    seed = ((chroma >= 28) & (low < 200)) | (high < 160)
    if not np.any(seed):
        raise ValueError(f'No foreground at stage {stage}')
    distance, nearest = distance_transform_edt(~seed, return_indices=True)
    near_rgb = rgb[nearest[0], nearest[1]]
    near_chroma = np.maximum(near_rgb.max(axis=2) - near_rgb.min(axis=2), 16)
    alpha = np.clip((chroma - 3) / np.maximum(near_chroma - 3, 1), 0, 1)
    alpha = np.where(high < 170, 1, alpha)
    alpha = np.where(seed, 1, alpha)
    alpha = np.where(distance <= 8, alpha, 0)
    mix = np.clip((alpha - .85) / .15, 0, 1)[..., None]
    color = np.clip(rgb * mix + near_rgb * (1-mix), 0, 255)
    # Correct pale checker-contaminated borders without recolouring red stems.
    core = seed & (high < 170) & (chroma > 35)
    if np.any(core):
        indices = distance_transform_edt(~core, return_distances=False, return_indices=True)
        edge = distance_transform_edt(alpha > .8)
        weight = (np.clip((low - 100) / 65, 0, 1) * np.clip((3-edge) / 2, 0, 1))[..., None]
        color = color * (1-weight) + rgb[indices[0], indices[1]] * weight
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    # Discard disconnected checker remnants and parts of adjacent plants.
    labels, count = label(alpha >= .38, structure=np.ones((3, 3), dtype=np.uint8))
    if not count:
        raise ValueError(f'No connected crop at stage {stage}')
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    keep = binary_dilation(labels == int(np.argmax(sizes)), structure=np.ones((5, 5)))
    rgba[~keep] = 0
    if stage == 3:
        # The fifth and sixth plants touch on the supplied sheet. Remove a
        # narrow fragment of its neighbour at the left edge of the last crop.
        rgba[160:325, :12] = 0
    rgba[rgba[..., 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    bbox = plant.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError(f'Empty stage {stage}')
    x0, y0, x1, y1 = bbox
    plant = plant.crop((max(0, x0-2), max(0, y0-2), min(plant.width, x1+2), min(plant.height, y1+2)))
    height = HEIGHTS[stage]
    width = max(1, round(plant.width * height / plant.height))
    if width > SIZE:
        width, height = SIZE, round(plant.height * SIZE / plant.width)
    plant = plant.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    # Place the lowest nontransparent stem pixel exactly on the soil plane.
    bottom = plant.getchannel('A').getbbox()[3]
    canvas.paste(plant, ((SIZE-width)//2, SIZE-bottom))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for stage in range(4):
        prepare_stage(stage).save(BLOCKS / f'beetroots_stage_{stage}.png', optimize=True)
    print('Prepared four beetroot growth stages.')


if __name__ == '__main__':
    main()
