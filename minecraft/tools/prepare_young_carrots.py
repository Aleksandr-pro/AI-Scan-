#!/usr/bin/env python3
"""Prepare early carrot crop stages from the supplied growth photograph.

Run from the repository root. Requires Pillow, numpy, scipy and opencv-python-headless.
Use plants 1, 3 and 4 of the image for stages 0, 1 and 2 respectively. Their
roots are cropped at the ground. The existing mature stage 3 remains unchanged.
"""
from pathlib import Path
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageOps

SOURCE = Path('minecraft/carrot-reference/growth.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
# Boxes end at the soil plane, leaving only the small top of the carrot.
CROPS = {0: (30, 420, 150, 560), 1: (305, 265, 505, 565), 2: (495, 165, 745, 560)}
HEIGHTS = {0: 96, 1: 160, 2: 310}


def prepare_stage(stage):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 848):
            raise ValueError('Expected the supplied 1264x848 carrot growth photo')
        rgb = np.asarray(image.crop(CROPS[stage]), dtype=np.float32)
    # White background removal with a soft transition for detailed leaves.
    distance = 255.0 - rgb.min(axis=2)
    alpha = np.clip((distance - 5.0) / 28.0, 0.0, 1.0)
    color = np.clip((rgb - 255.0 * (1.0 - alpha[..., None])) /
                    np.maximum(alpha[..., None], 1.0 / 255.0), 0, 255)
    # JPEG white matte contaminates pale, partially covered leaf edges. Use
    # the nearest strong leaf colour there, keeping the original soft alpha.
    solid = (alpha > .98) & (rgb.min(axis=2) < 150)
    if not np.any(solid):
        raise ValueError(f'No solid plant pixels for stage {stage}')
    nearest = distance_transform_edt(~solid, return_distances=False, return_indices=True)
    leaf_color = rgb[nearest[0], nearest[1]]
    weight = np.clip((rgb.min(axis=2) - 150.0) / 60.0, 0.0, 1.0)[..., None]
    color = color * (1.0 - weight) + leaf_color * weight
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    # Discard disconnected parts of neighbours at the edges. Dilate the
    # chosen component slightly to retain its original antialiased leaf tips.
    count, labels, stats, _ = cv2.connectedComponentsWithStats((alpha >= .25).astype(np.uint8), 8)
    if count < 2:
        raise ValueError(f'No foliage found for stage {stage}')
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = cv2.dilate((labels == main).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    rgba[~keep] = 0
    plant = Image.fromarray(rgba)
    bbox = plant.getchannel('A').getbbox()
    if bbox is None:
        raise ValueError(f'Empty stage {stage}')
    plant = plant.crop(bbox)
    height = HEIGHTS[stage]
    width = max(1, round(plant.width * height / plant.height))
    if width > SIZE:
        raise ValueError('Unexpected plant proportions')
    plant = plant.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(plant, ((SIZE-width)//2, SIZE-height))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for stage in range(3):
        prepare_stage(stage).save(BLOCKS / f'carrots_stage_{stage}.png', optimize=True)
    print('Prepared carrot crop stages 0..2 from the supplied growth photo.')


if __name__ == '__main__':
    main()
