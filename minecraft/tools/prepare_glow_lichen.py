#!/usr/bin/env python3
"""Extract three flat glow-lichen overlays from the user's JPG.

Run from the repo root. Requires Pillow, numpy and scipy. The photo contains
both black background and rock/moss; colour segmentation is approximate.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/glow-lichen-reference/glow-lichen.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 256
BOXES = ((0,0,395,840), (395,125,854,710), (860,110,1264,785))


def variant(index):
    with Image.open(SOURCE) as source:
        source = ImageOps.exif_transpose(source).convert('RGB')
        if source.size != (1264,848):
            raise ValueError('Unexpected glow-lichen image size')
        rgb = np.asarray(source.crop(BOXES[index]), dtype=np.float32)
    red, green, blue = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    # Green/yellow chroma distinguishes luminous lobes from neutral gray rock;
    # luminance rejects black JPEG noise and most dark underlying rock. Dark
    # green moss and gray-green lichen cannot be separated perfectly in a JPG.
    color = np.clip((green-blue-16)/18, 0, 1)
    brightness = np.clip((green-48)/22, 0, 1)
    not_magenta = np.clip((green-red+12)/15, 0, 1)
    alpha = color*brightness*not_magenta
    labels, count = label(alpha >= .4, structure=np.ones((3,3), dtype=np.uint8))
    if not count:
        raise ValueError(f'No lichen detected in region {index}')
    counts = np.bincount(labels.ravel())
    keep = counts >= 20
    keep[0] = False
    keep = binary_dilation(keep[labels], structure=np.ones((3,3)))
    alpha *= keep
    pixels = np.dstack((rgb.astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    pixels[pixels[:,:,3] == 0, :3] = 0
    plant = Image.fromarray(pixels)
    bbox = plant.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError('No lichen after extraction')
    x0,y0,x1,y1 = bbox
    plant = plant.crop((max(0,x0-2),max(0,y0-2),min(plant.width,x1+2),min(plant.height,y1+2)))
    plant.thumbnail((SIZE-6,SIZE-6), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE,SIZE), (0,0,0,0))
    canvas.paste(plant, ((SIZE-plant.width)//2,(SIZE-plant.height)//2))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i in range(len(BOXES)):
        name = 'glow_lichen' if i == 0 else f'glow_lichen_variant_{i}'
        variant(i).save(BLOCKS / (name+'.png'), optimize=True)
    print('Prepared three transparent glow-lichen variants.')


if __name__ == '__main__':
    main()
