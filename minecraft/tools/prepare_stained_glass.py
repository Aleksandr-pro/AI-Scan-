#!/usr/bin/env python3
"""Prepare three framed, tinted glass blocks from opaque JPG images.

Run from repo root with Pillow. The checkerboard is drawn into the JPEG,
not an alpha channel: replace it with a uniform translucent coloured centre.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

REFERENCE=Path('minecraft/stained-glass-reference')
BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
SIZE=256
# Measured against the 1024x1024 supplied images; outer crop removes the
# checkerboard outside the frame, inner rectangle removes the baked grid.
OUTER=(9,9,1015,1015)
INNER=(48,48,976,976)
# Photo does not contain real alpha. Centre tint and opacity are deliberate
# approximations, kept below vanilla's 102/255 centre opacity.
TINTS={'black':(25,25,25,90), 'white':(255,255,255,60), 'pink':(242,145,182,85)}


def prepare(color):
    if color not in TINTS:raise ValueError('Unknown glass colour')
    with Image.open(REFERENCE/f'{color}.jpg') as original:
        image=ImageOps.exif_transpose(original).convert('RGB')
        if image.size!=(1024,1024):raise ValueError('Unexpected glass source size')
        image=image.convert('RGBA')
    ImageDraw.Draw(image).rectangle((INNER[0],INNER[1],INNER[2]-1,INNER[3]-1),fill=TINTS[color])
    # Pillow resizes RGBA in premultiplied alpha; no checkerboard fringe from
    # the hidden source centre is mixed into the transparent region.
    return image.crop(OUTER).resize((SIZE,SIZE),Image.Resampling.LANCZOS)


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for color in TINTS:
        prepare(color).save(BLOCKS/f'photo_stained_glass_{color}.png',optimize=True)
    print('Prepared black, white and pink translucent framed glass blocks.')


if __name__=='__main__':main()
