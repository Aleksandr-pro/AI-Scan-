#!/usr/bin/env python3
"""Extract lily-pad variations and moss tiles from the user's white-background JPG.

Run from repo root; requires Pillow, numpy and scipy. Flower and edge extraction
is approximate. Moss variants share an edge tile and preserve distinct interiors.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, grey_erosion, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/moss-lily-reference/moss-lilies.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 256
LILY_BOXES = ((60,0,505,210), (530,0,922,210), (918,55,1202,212),
              (54,215,480,390), (548,215,836,355), (930,215,1180,355))
MOSS_BOXES = ((80,550,240,710), (35,550,195,710),
              (180,500,340,660), (535,500,695,660))


def load():
    with Image.open(SOURCE) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        if im.size != (1264, 848):
            raise ValueError('Unexpected source image size')
        return im.copy()


def lily(index):
    rgb = np.asarray(load().crop(LILY_BOXES[index]), dtype=np.float32)
    # The illustration is against almost pure white. Preserve off-white petals
    # as much as possible while removing the backdrop and its JPEG artifacts.
    alpha = np.clip((255 - rgb.min(axis=2) - 3) / 22, 0, 1)
    labels, count = label(alpha >= .35, structure=np.ones((3,3), dtype=np.uint8))
    if not count:
        raise ValueError('Empty lily crop')
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    region = binary_dilation(labels == int(np.argmax(sizes)), structure=np.ones((5,5)))
    # Undo white compositing at partly transparent edges.
    color = np.clip((rgb - (1-alpha[...,None])*255) / np.maximum(alpha[...,None], 1/255), 0, 255)
    # Contract the outer mask a little: the JPG bakes white edge pixels into
    # the object outline. Some delicate petals may be softened as a tradeoff.
    alpha = grey_erosion(alpha, size=(5,5))
    pixels = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    pixels[~region] = 0
    pixels[pixels[:,:,3] == 0, :3] = 0
    im = Image.fromarray(pixels)
    bbox = im.getchannel('A').point(lambda v: 255 if v >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError('No lily after masking')
    x0,y0,x1,y1 = bbox
    im = im.crop((max(0,x0-2), max(0,y0-2), min(im.width,x1+2), min(im.height,y1+2)))
    # Source is photographed obliquely. Gently undo the foreshortening for a
    # horizontal lily-pad plane, rather than treating it as a vertical plant.
    correction = 1.25 if index == 1 else 1.55
    im = im.resize((im.width, round(im.height*correction)), Image.Resampling.LANCZOS)
    im.thumbnail((SIZE-12, SIZE-12), Image.Resampling.LANCZOS)
    out = Image.new('RGBA', (SIZE,SIZE), (0,0,0,0))
    out.paste(im, ((SIZE-im.width)//2, (SIZE-im.height)//2))
    return out


def periodic(image, width=40):
    """Average opposite edge neighborhoods; the outermost rows match exactly."""
    a = np.asarray(image, dtype=np.float32).copy()
    for axis in (1,0):
        src = a.copy()
        for d in range(width):
            w = .5 * (1 - d/(width-1))
            if axis == 1:
                a[:,d] = src[:,d]*(1-w) + src[:,-1-d]*w
                a[:,-1-d] = src[:,-1-d]*(1-w) + src[:,d]*w
            else:
                a[d,:] = src[d,:]*(1-w) + src[-1-d,:]*w
                a[-1-d,:] = src[-1-d,:]*(1-w) + src[d,:]*w
    return Image.fromarray(np.rint(a).astype(np.uint8), 'RGB')


def moss():
    im = load()
    patches = [im.crop(box).resize((SIZE,SIZE), Image.Resampling.LANCZOS) for box in MOSS_BOXES]
    base = periodic(patches[0])
    # All variants share exactly the same 32px border. Distinct photographic
    # interiors fade gently into it so neighboring moss blocks meet cleanly.
    x,y = np.meshgrid(np.arange(SIZE), np.arange(SIZE))
    distance = np.minimum.reduce([x,y,SIZE-1-x,SIZE-1-y])
    blend = np.clip((distance-32)/48, 0, 1)
    blend = blend*blend*(3-2*blend)
    mask = Image.fromarray(np.rint(blend*255).astype(np.uint8))
    return [base] + [Image.composite(patch, base, mask) for patch in patches[1:]]


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i in range(len(LILY_BOXES)):
        name = 'waterlily' if i == 0 else f'waterlily_variant_{i}'
        lily(i).save(BLOCKS / (name+'.png'), optimize=True)
    for i, image in enumerate(moss()):
        name = 'moss_block' if i == 0 else f'moss_block_variant_{i}'
        image.save(BLOCKS / (name+'.png'), optimize=True)
    print('Prepared six lily pads and four moss tiles.')


if __name__ == '__main__':
    main()
