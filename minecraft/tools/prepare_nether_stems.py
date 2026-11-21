#!/usr/bin/env python3
"""Split supplied Nether stem photos into top and bark faces.

Both photos have a thin divider; crop away that divider and resize each square
separately. Keep the end-grain design intact. Make bark tileable on both axes
with a narrow symmetric edge blend, without turning the vertical grain.
Requires Pillow and numpy; run from the repository root.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE=Path('minecraft/nether-stems-reference')
BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
SIZE=256
BOXES={'top':(3,0,723,720), 'side':(733,0,1453,720)}


def periodic_bark(image):
    a=np.asarray(image,dtype=np.float32).copy()
    for axis,width in ((1,20),(0,14)):
        source=a.copy()
        for d in range(width):
            t=1-d/(width-1);weight=.5*t*t*(3-2*t)
            if axis==1:
                a[:,d]=source[:,d]*(1-weight)+source[:,-1-d]*weight
                a[:,-1-d]=source[:,-1-d]*(1-weight)+source[:,d]*weight
            else:
                a[d,:]=source[d,:]*(1-weight)+source[-1-d,:]*weight
                a[-1-d,:]=source[-1-d,:]*(1-weight)+source[d,:]*weight
    return Image.fromarray(np.rint(a).clip(0,255).astype(np.uint8))


def prepare(kind,face):
    with Image.open(SOURCE/(kind+'.jpg')) as src:
        src=ImageOps.exif_transpose(src).convert('RGB')
        if src.size!=(1456,720):raise ValueError('Unexpected source image size')
        im=src.crop(BOXES[face]).resize((SIZE,SIZE),Image.Resampling.LANCZOS)
    return periodic_bark(im) if face=='side' else im


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for kind in ('crimson','warped'):
        for face in ('top','side'):
            output=BLOCKS/f'photo_{kind}_stem_{face}.png'
            prepare(kind,face).save(output,optimize=True)
            print('Prepared',output)


if __name__=='__main__':main()
