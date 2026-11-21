#!/usr/bin/env python3
"""Prepare red crimson and teal warped plank tiles from the user's photos.

Six full horizontal courses are cropped between joints. Only the edges are
blended for tiling; colors, wood grain, and orientation come from the photos.
Run from the repository root; requires Pillow and numpy.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE=Path('minecraft/nether-planks-reference')
BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
SIZE=256
CROPS={'warped':(0,93,1024,854), 'crimson':(0,95,1024,844)}


def prepare(kind):
    with Image.open(SOURCE/(kind+'.jpg')) as src:
        src=ImageOps.exif_transpose(src).convert('RGB')
        if src.size!=(1024,1024):raise ValueError('Unexpected source size')
        img=src.crop(CROPS[kind]).resize((SIZE,SIZE),Image.Resampling.LANCZOS)
    a=np.asarray(img,dtype=np.float32).copy()
    # Blend the horizontal grain across the left/right seam; vertical bounds
    # already land on plank joints, so keep that blend especially narrow.
    for axis,width in ((1,18),(0,3)):
        original=a.copy()
        for d in range(width):
            t=1-d/(width-1);weight=.5*t*t*(3-2*t)
            if axis==1:
                a[:,d]=original[:,d]*(1-weight)+original[:,-1-d]*weight
                a[:,-1-d]=original[:,-1-d]*(1-weight)+original[:,d]*weight
            else:
                a[d,:]=original[d,:]*(1-weight)+original[-1-d,:]*weight
                a[-1-d,:]=original[-1-d,:]*(1-weight)+original[d,:]*weight
    return Image.fromarray(np.rint(a).clip(0,255).astype(np.uint8))


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for kind in CROPS:
        output=BLOCKS/f'photo_{kind}_planks.png'
        prepare(kind).save(output,optimize=True)
        print('Prepared',output)


if __name__=='__main__':main()
