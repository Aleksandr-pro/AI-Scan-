#!/usr/bin/env python3
"""Extract the fourth and fifth plants for wheat stages 5 and 6.

Run from the repository root; requires Pillow, numpy, opencv-python-headless.
The supplied WebP already contains alpha. Keep its translucent fine edges,
remove disconnected slivers of adjacent plants, and anchor each stalk at soil.
Earlier and fully mature stages and the wheat item are not modified.
"""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

SOURCE = Path('minecraft/wheat-reference/intermediate.webp')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
# Crop bounds in the supplied 1536x1024 sheet. The fourth and fifth plants.
CROPS = {5: (887, 100, 1215, 930), 6: (1205, 100, 1536, 930)}
HEIGHTS = {5: 460, 6: 492}


def prepare_stage(stage):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source)
        if image.size != (1536, 1024) or image.mode != 'RGBA':
            raise ValueError('Expected the supplied transparent 1536x1024 WebP')
        rgba = np.array(image.crop(CROPS[stage]), dtype=np.uint8)
    alpha = rgba[:, :, 3]
    # Isolate the large plant from fragments of neighbouring plants at the
    # crop edges. A small dilation restores the original antialiasing around
    # the selected component without turning those fragments opaque.
    count, labels, stats, _ = cv2.connectedComponentsWithStats((alpha >= 64).astype(np.uint8), 8)
    if count < 2:
        raise ValueError(f'No plant found for stage {stage}')
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    selected = (labels == main).astype(np.uint8)
    keep = cv2.dilate(selected, np.ones((5, 5), np.uint8)) > 0
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
    for stage in (5, 6):
        prepare_stage(stage).save(BLOCKS / f'wheat_stage_{stage}.png', optimize=True)
    print('Prepared wheat stages 5 and 6 from the intermediate growth photo.')


if __name__ == '__main__':
    main()
