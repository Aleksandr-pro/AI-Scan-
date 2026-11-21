#!/usr/bin/env python3
"""Prepare animated short and double-height Bedrock seagrass from user art.

Requires Pillow, numpy, scipy and opencv-python-headless; run from repo root.
Uses vanilla 18/19-frame strip layouts, leaving vanilla flipbook metadata intact.
Tall halves are generated from the same swaying 96x192 canvas per frame.
"""
from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import binary_dilation, label

SOURCE = Path('minecraft/water-plant-reference/water-plants.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 96
SHORT_FRAMES = 18
TALL_FRAMES = 19


def plant():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (444, 840):
            raise ValueError('Unexpected source image dimensions')
        rgb = np.asarray(image, dtype=np.float32)
    alpha = np.clip((rgb.max(axis=2) - 5) / 24, 0, 1)
    color = np.clip(rgb / np.maximum(alpha[..., None], 1/255), 0, 255)
    labels, count = label(alpha >= .3, structure=np.ones((3,3), dtype=np.uint8))
    if not count:
        raise ValueError('No visible water plant')
    counts = np.bincount(labels.ravel())
    keep = counts >= 20
    keep[0] = False
    region = binary_dilation(keep[labels], structure=np.ones((5,5)))
    pixels = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    pixels[~region] = 0
    pixels[pixels[:,:,3] == 0, :3] = 0
    result = Image.fromarray(pixels)
    bbox = result.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if not bbox:
        raise ValueError('Empty water plant')
    x0,y0,x1,y1 = bbox
    return result.crop((max(0,x0-2), max(0,y0-2), min(result.width,x1+2), min(result.height,y1+2)))


def canvas(height):
    source = plant()
    # Reserve space on both sides for animated motion and use the same aspect
    # ratio on both halves of the tall plant.
    source.thumbnail((SIZE-12, height-4), Image.Resampling.LANCZOS)
    out = Image.new('RGBA', (SIZE, height), (0,0,0,0))
    bottom = source.getchannel('A').getbbox()[3]
    out.paste(source, ((SIZE-source.width)//2, height-bottom))
    return out


def sway(base, index, count):
    """Mild, periodic, rooted displacement; premultiplication avoids halos."""
    data = np.asarray(base, dtype=np.float32) / 255
    alpha = data[:,:,3:4]
    premul = np.concatenate((data[:,:,:3]*alpha, alpha), axis=2)
    height, width = data.shape[:2]
    x,y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    pos = (height-1-y)/(height-1)
    shift = 3.0 * pos * np.sin(2*math.pi*index/count + pos*0.7)
    moved = cv2.remap(premul, x-shift, y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = moved[:,:,3:4]
    rgb = np.where(a > 0, moved[:,:,:3]/np.maximum(a, 1/255), 0)
    result = np.rint(np.clip(np.concatenate((rgb,a), axis=2),0,1)*255).astype(np.uint8)
    result[result[:,:,3] == 0, :3] = 0
    return Image.fromarray(result)


def strips():
    short = canvas(SIZE)
    tall = canvas(SIZE*2)
    result = {'seagrass.png': Image.new('RGBA', (SIZE, SIZE*SHORT_FRAMES))}
    for side in 'ab':
        for half in ('bottom', 'top'):
            result[f'seagrass_doubletall_{half}_{side}.tga'] = Image.new('RGBA', (SIZE, SIZE*TALL_FRAMES))
    for i in range(SHORT_FRAMES):
        result['seagrass.png'].paste(sway(short, i, SHORT_FRAMES), (0, i*SIZE))
    for i in range(TALL_FRAMES):
        frame = sway(tall, i, TALL_FRAMES)
        for side in 'ab':
            oriented = frame if side == 'a' else ImageOps.mirror(frame)
            result[f'seagrass_doubletall_top_{side}.tga'].paste(oriented.crop((0,0,SIZE,SIZE)), (0,i*SIZE))
            result[f'seagrass_doubletall_bottom_{side}.tga'].paste(oriented.crop((0,SIZE,SIZE,SIZE*2)), (0,i*SIZE))
    return result


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for name, image in strips().items():
        image.save(BLOCKS / name)
    print('Prepared animated short and double-height seagrass.')


if __name__ == '__main__':
    main()
