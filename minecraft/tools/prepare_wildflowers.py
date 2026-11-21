#!/usr/bin/env python3
"""Extract supplied wildflowers and the two-block rose bush from the JPG.

Run from repository root. Requires Pillow, numpy and scipy. Each flower is selected
from its own region of the photograph and the near-black JPG background is
removed approximately. Some blooms have no exact vanilla equivalent: see README.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/flower-reference/flowers.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 256
# Ten one-block images in reading order. The ninth and tenth are optional
# variants of allium and dandelion, respectively.
FLOWERS = {
    'flower_oxeye_daisy': (0, 0, 225, 387),
    'flower_cornflower': (225, 0, 407, 387),
    'flower_rose': (407, 0, 588, 387),
    'flower_allium': (588, 0, 775, 387),
    'flower_dandelion': (775, 0, 957, 387),
    'flower_houstonia': (0, 388, 225, 702),
    'flower_blue_orchid': (225, 388, 407, 702),
    'flower_lily_of_the_valley': (407, 388, 588, 702),
    'photo_flower_violet': (588, 388, 775, 702),
    'photo_flower_buttercup': (775, 388, 957, 702),
}
ROSE = (957, 45, 1456, 705)


def extract(box):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1456, 720):
            raise ValueError('Expected the supplied 1456x720 flower JPG')
        rgb = np.asarray(image.crop(box), dtype=np.float32)
    # Intensity, not just green, retains red, purple, blue and pale flowers.
    alpha = np.clip((rgb.max(axis=2) - 5.0) / 24.0, 0, 1)
    color = np.clip(rgb / np.maximum(alpha[..., None], 1/255), 0, 255)
    pixels = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    # Drop isolated JPEG specks and small slivers from adjacent flowers while
    # preserving the selected plant and its antialiased immediate boundary.
    labels, count = label(alpha >= .25, structure=np.ones((3, 3), dtype=np.uint8))
    if not count:
        raise ValueError(f'No connected flower in region {box}')
    counts = np.bincount(labels.ravel()); counts[0] = 0
    keep = binary_dilation(labels == int(np.argmax(counts)), structure=np.ones((5, 5)))
    pixels[~keep] = 0
    pixels[pixels[:, :, 3] == 0, :3] = 0
    plant = Image.fromarray(pixels)
    bbox = plant.getchannel('A').point(lambda v: 255 if v >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError(f'Empty flower region {box}')
    x0, y0, x1, y1 = bbox
    return plant.crop((max(0, x0-2), max(0, y0-2), min(plant.width, x1+2), min(plant.height, y1+2)))


def on_canvas(box, height):
    plant = extract(box)
    plant.thumbnail((SIZE-8, height-8), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, height), (0, 0, 0, 0))
    bottom = plant.getchannel('A').getbbox()[3]
    canvas.paste(plant, ((SIZE-plant.width)//2, height-bottom))
    return canvas


def flower(name):
    return on_canvas(FLOWERS[name], SIZE)


def rose():
    return on_canvas(ROSE, SIZE*2)


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for name in FLOWERS:
        flower(name).save(BLOCKS / f'{name}.png', optimize=True)
    plant = rose()
    plant.crop((0, 0, SIZE, SIZE)).save(BLOCKS / 'double_plant_rose_top.png', optimize=True)
    plant.crop((0, SIZE, SIZE, SIZE*2)).save(BLOCKS / 'double_plant_rose_bottom.png', optimize=True)
    print('Prepared ten field-flower images and both halves of the rose bush.')


if __name__ == '__main__':
    main()
