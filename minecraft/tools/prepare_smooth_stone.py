#!/usr/bin/env python3
"""Prepare smooth-stone block and slab textures from the supplied photograph.

The slab side is two repeated half-height faces, so the usual top- or bottom-
slab UV slice contains a complete border. This is a texture, not a new model.
"""
from pathlib import Path
from PIL import Image, ImageOps

SOURCE=Path('minecraft/smooth-stone-reference/smooth-stone.jpg')
BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
BOX=(221,35,1043,808)


def make_textures():
    with Image.open(SOURCE) as original:
        image=ImageOps.exif_transpose(original).convert('RGB')
    if image.size != (1264,843):raise ValueError('Unexpected source dimensions')
    face=image.crop(BOX).resize((256,256),Image.Resampling.LANCZOS)
    half=face.resize((128,64),Image.Resampling.LANCZOS)
    side=Image.new('RGB',(128,128))
    side.paste(half,(0,0));side.paste(half,(0,64))
    return face,side


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for image,name in zip(make_textures(),('photo_smooth_stone','photo_smooth_stone_slab_side')):
        image.save(BLOCKS/(name+'.png'),optimize=True)
        print('Prepared',name)


if __name__=='__main__':main()
