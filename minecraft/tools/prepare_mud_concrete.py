#!/usr/bin/env python3
"""Prepare the user-provided mud and concrete photos (requires Pillow).

Run from the repository root. Keep the staggered brick pattern intact; only a
narrow edge strip is blended. The concrete gets a wider, organic photo wrap.
"""
from pathlib import Path
from PIL import Image, ImageOps
from prepare_cobblestone import prepare

ROOT=Path('minecraft')
REF=ROOT/'mud-concrete-reference'
BLOCKS=ROOT/'realistic-dirt/textures/blocks'
SIZE=512


def match_edges(img, width):
    # Matching opposite pixels at the seam while retaining the photograph's
    # natural pattern and relief. Only a narrow strip is touched.
    for d in range(width):
        t=1-d/width
        a=.5*t*t*(3-2*t)
        left=img.crop((d,0,d+1,SIZE)); right=img.crop((SIZE-1-d,0,SIZE-d,SIZE))
        img.paste(Image.blend(left,right,a),(d,0))
        img.paste(Image.blend(right,left,a),(SIZE-1-d,0))
    for d in range(width):
        t=1-d/width
        a=.5*t*t*(3-2*t)
        top=img.crop((0,d,SIZE,d+1)); bottom=img.crop((0,SIZE-1-d,SIZE,SIZE-d))
        img.paste(Image.blend(top,bottom,a),(0,d))
        img.paste(Image.blend(bottom,top,a),(0,SIZE-1-d))
    return img


def brick_tile(path):
    with Image.open(path) as source:
        img=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),(SIZE,SIZE),Image.Resampling.LANCZOS)
    return match_edges(img, 12)


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for name,image in [('packed_mud',brick_tile(REF/'packed-mud.jpg')),
                       ('concrete_white',match_edges(prepare(REF/'white-concrete.jpg'), 4)),
                       ('concrete_red',match_edges(prepare(REF/'red-concrete.jpg'), 4))]:
        image.save(BLOCKS/f'{name}.png',optimize=True)
        print(f'{name}: {image.size}, RGB')

if __name__=='__main__':main()
