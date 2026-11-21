#!/usr/bin/env python3
"""Prepare white shulker UV atlas using vanilla geometry and user photos.

Run from repo root with Pillow. The white mob shares this vanilla texture path;
the face/head pixels remain vanilla, but its outer shell can change too.
"""
from pathlib import Path
from PIL import Image, ImageOps

REFERENCE=Path('minecraft/white-shulker-reference')
ROOT=Path('minecraft/realistic-dirt')
ENTITY=ROOT/'textures/entity/shulker/shulker_white.png'
ICON=ROOT/'textures/blocks/shulker_top_white.png'
SCALE=8


def photo(name,size):
    with Image.open(REFERENCE/f'{name}.jpg') as im:
        im=ImageOps.exif_transpose(im).convert('RGB')
        if im.size!=(1024,1024):
            raise ValueError('Unexpected white shulker image')
        return im.resize((size,size),Image.Resampling.LANCZOS)


def textures():
    with Image.open(REFERENCE/'vanilla-white.png') as im:
        if im.size!=(64,64):
            raise ValueError('Unexpected vanilla UV atlas size')
        atlas=im.convert('RGBA').resize((64*SCALE,64*SCALE),Image.Resampling.NEAREST)
    unit=16*SCALE
    body=photo('body',unit).convert('RGBA'); top=photo('top',unit).convert('RGBA')
    def paste(image,x,y): atlas.paste(image,(x*SCALE,y*SCALE))
    paste(top,16,0);paste(body,32,0);paste(body,16,28);paste(body,32,28)
    for x in (0,16,32,48):
        paste(body.crop((0,0,unit,12*SCALE)),x,16)
        paste(body.crop((0,8*SCALE,unit,16*SCALE)),x,44)
    return atlas,photo('top',256)


def main():
    atlas,icon=textures()
    ENTITY.parent.mkdir(parents=True,exist_ok=True);ICON.parent.mkdir(parents=True,exist_ok=True)
    atlas.save(ENTITY,optimize=True);icon.save(ICON,optimize=True)
    print('Prepared white shulker UV atlas and inventory texture.')


if __name__=='__main__':main()
