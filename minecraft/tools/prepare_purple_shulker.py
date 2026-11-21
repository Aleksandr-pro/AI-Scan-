#!/usr/bin/env python3
"""Build purple shulker-box textures using Bedrock's 64x64 shulker UV layout.

Run from repo root; requires Pillow. The purple shulker mob shares the vanilla
entity-texture path, so it may also change. Its head region is kept from vanilla.
"""
from pathlib import Path
from PIL import Image, ImageOps

REFERENCE = Path('minecraft/shulker-reference')
ROOT = Path('minecraft/realistic-dirt')
ENTITY = ROOT/'textures/entity/shulker/shulker_purple.png'
ICON = ROOT/'textures/blocks/shulker_top_purple.png'
SCALE = 8  # each 16x16 face is 128x128; the 64x64 atlas is 512x512


def photo(name, size):
    with Image.open(REFERENCE/f'{name}.jpg') as image:
        image=ImageOps.exif_transpose(image).convert('RGB')
        if image.size != (1024,1024):
            raise ValueError('Unexpected reference size')
        return image.resize((size,size),Image.Resampling.LANCZOS)


def textures():
    with Image.open(REFERENCE/'vanilla-purple.png') as vanilla:
        if vanilla.size != (64,64):
            raise ValueError('Unexpected vanilla shulker atlas')
        atlas=vanilla.convert('RGBA').resize((64*SCALE,64*SCALE),Image.Resampling.NEAREST)
    unit=16*SCALE
    body=photo('body',unit).convert('RGBA')
    top=photo('top',unit).convert('RGBA')
    def paste(im,x,y):
        atlas.paste(im,(x*SCALE,y*SCALE))
    # Cube UV layout in Bedrock samples: lid (16x12x16), origin UV 0,0;
    # base (16x8x16), origin UV 0,28. The head area at y>=52 remains vanilla.
    paste(top,16,0)       # lid top
    paste(body,32,0)      # lid underside
    paste(body,16,28)     # base top, visible when opened
    paste(body,32,28)     # base bottom
    for x in (0,16,32,48):
        paste(body.crop((0,0,unit,12*SCALE)),x,16)
        paste(body.crop((0,8*SCALE,unit,16*SCALE)),x,44)
    return atlas,photo('top',256)


def main():
    atlas,icon=textures()
    ENTITY.parent.mkdir(parents=True,exist_ok=True)
    ICON.parent.mkdir(parents=True,exist_ok=True)
    atlas.save(ENTITY,optimize=True)
    icon.save(ICON,optimize=True)
    print('Prepared purple shulker entity atlas and inventory texture.')


if __name__=='__main__':
    main()
