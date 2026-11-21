#!/usr/bin/env python3
"""Prepare four Bedrock potato crop textures from the supplied growth JPG.

Run from repository root. Requires Pillow, numpy and scipy. The JPEG has a
baked checkerboard, including behind nearly white flowers: the white petals
need approximate hand-guided masks to avoid keeping the checker pattern.
We use plants 1, 3, 5 and 6; plant 6 is full-grown without exposed tubers.
"""
from pathlib import Path
import math
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label
from PIL import Image, ImageDraw, ImageOps

SOURCE = Path('minecraft/potato-reference/growth.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
CROPS = {0: (0, 525, 112, 630), 1: (240, 410, 442, 630),
         2: (620, 245, 823, 630), 3: (822, 190, 1042, 632)}
HEIGHTS = {0: 160, 1: 256, 2: 352, 3: 460}
# Original-photo positions and approximate petal sizes. The petals are very
# pale against the checker; these masks approximate their silhouettes.
FLOWERS = {2: ((707, 276, 12), (677, 303, 11), (742, 318, 11), (725, 327, 8)),
           3: ((884, 239, 12), (909, 270, 16), (938, 220, 14), (962, 258, 10))}


def petal_mask(stage, size):
    # Draw subpixel-smoothed elliptical petals near the photographed centres.
    mask = Image.new('L', (size[0]*3, size[1]*3), 0)
    draw = ImageDraw.Draw(mask)
    x0, y0, _, _ = CROPS[stage]
    for cx, cy, radius in FLOWERS.get(stage, ()):
        cx, cy = (cx-x0)*3, (cy-y0)*3
        r = radius*3
        for j in range(5):
            angle = math.pi * 2 * j / 5 - math.pi / 2
            ux, uy = math.cos(angle), math.sin(angle)
            vx, vy = -uy, ux
            # A tapered oval: point at centre, wide middle, pointed tip.
            pts = [(cx + ux*t*r + vx*w*r, cy + uy*t*r + vy*w*r)
                   for t, w in ((.16, 0), (.36, .16), (.68, .17), (1, 0), (.68, -.17), (.36, -.16))]
            draw.polygon(pts, fill=255)
    return np.asarray(mask.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 255


def prepare_stage(stage):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 843):
            raise ValueError('Expected the supplied 1264x843 JPG')
        rgb = np.asarray(image.crop(CROPS[stage]), dtype=np.float32)
    high, low = rgb.max(axis=2), rgb.min(axis=2)
    chroma = high - low
    seed = ((chroma >= 28) & (low < 200)) | (high < 160)
    if not np.any(seed):
        raise ValueError(f'No foreground for stage {stage}')
    distance, nearest = distance_transform_edt(~seed, return_indices=True)
    nearest_rgb = rgb[nearest[0], nearest[1]]
    nearest_chroma = np.maximum(nearest_rgb.max(axis=2) - nearest_rgb.min(axis=2), 16)
    alpha = np.clip((chroma - 3) / np.maximum(nearest_chroma - 3, 1), 0, 1)
    alpha = np.where(high < 170, 1, alpha)
    alpha = np.where(seed, 1, alpha)
    alpha = np.where(distance <= 8, alpha, 0)
    mix = np.clip((alpha - .85) / .15, 0, 1)[..., None]
    color = np.clip(rgb * mix + nearest_rgb * (1 - mix), 0, 255)
    core = seed & (high < 170) & (chroma > 35)
    if np.any(core):
        indices = distance_transform_edt(~core, return_distances=False, return_indices=True)
        edge = distance_transform_edt(alpha > .8)
        weight = (np.clip((low - 100) / 65, 0, 1) * np.clip((3 - edge) / 2, 0, 1))[..., None]
        color = color * (1-weight) + rgb[indices[0], indices[1]] * weight
    # Approximate pale petals that cannot be separated from a neutral checker
    # by colour alone. Protect coloured stems, yellow flower centres and leaves.
    petals = petal_mask(stage, (rgb.shape[1], rgb.shape[0]))
    pale = (low > 155) & (chroma < 45)
    strength = petals * pale
    alpha = np.maximum(alpha, strength)
    brightness = np.clip(rgb.mean(axis=2) + 12, 225, 255)
    petal_rgb = np.stack((brightness, brightness, np.clip(brightness - 3, 0, 255)), axis=2)
    color = color * (1-strength[..., None]) + petal_rgb * strength[..., None]
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    # Keep the main plant and the hand-guided petals, remove neighbour slivers.
    labels, count = label(alpha >= .38, structure=np.ones((3, 3), dtype=np.uint8))
    if not count:
        raise ValueError(f'No connected crop at stage {stage}')
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    keep = binary_dilation(labels == int(np.argmax(sizes)), structure=np.ones((5, 5))) | (strength > 0)
    rgba[~keep] = 0
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
    canvas.paste(plant, ((SIZE-width)//2, SIZE-height))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for stage in range(4):
        prepare_stage(stage).save(BLOCKS / f'potatoes_stage_{stage}.png', optimize=True)
    print('Prepared all four potato growth stages.')


if __name__ == '__main__':
    main()
