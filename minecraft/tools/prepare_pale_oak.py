#!/usr/bin/env python3
"""Prepare one pale-oak plank tile from the supplied photograph.

Requires Pillow and numpy. Run from repo root. Crop between two board seams;
lightly blend opposite edges without rotating the horizontal plank courses.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

SOURCE=Path('minecraft/pale-oak-reference/planks.jpg')
OUTPUT=Path('minecraft/realistic-dirt/textures/blocks/pale_oak_planks.png')
SIZE=256
# Boundaries on board joints: five complete horizontal courses.
CROP=(0,157,1024,958)


def prepare():
    with Image.open(SOURCE) as image:
        image=ImageOps.exif_transpose(image).convert('RGB')
        if image.size!=(1024,1024):raise ValueError('Unexpected source size')
        image=image.crop(CROP).resize((SIZE,SIZE),Image.Resampling.LANCZOS)
    a=np.asarray(image,dtype=np.float32).copy()
    # Join left/right grain softly; vertical edges fall at an existing seam,
    # so use only a narrow vertical blend to avoid ghosting board lines.
    for axis,width in ((1,18),(0,3)):
        src=a.copy()
        for d in range(width):
            t=1-d/(width-1); weight=.5*t*t*(3-2*t)
            if axis==1:
                a[:,d]=src[:,d]*(1-weight)+src[:,-1-d]*weight
                a[:,-1-d]=src[:,-1-d]*(1-weight)+src[:,d]*weight
            else:
                a[d,:]=src[d,:]*(1-weight)+src[-1-d,:]*weight
                a[-1-d,:]=src[-1-d,:]*(1-weight)+src[d,:]*weight
    return Image.fromarray(np.rint(a).clip(0,255).astype(np.uint8))


def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    prepare().save(OUTPUT,optimize=True)
    print('Prepared repeating pale-oak planks.')


if __name__=='__main__':main()
