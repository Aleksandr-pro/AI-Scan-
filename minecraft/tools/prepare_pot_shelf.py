#!/usr/bin/env python3
"""Prepare oak-shelf and flower-pot Bedrock UV atlases from supplied photos.

Requires Pillow. UV regions follow vanilla 32x32 oak shelf / 16x16 pot
textures; shelf face ranges are cross-checked against the Java shelf model,
which matches the modern Bedrock UV layout. No game geometry is changed.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT=Path('minecraft')
REF=ROOT/'pot-shelf-reference'
OUT=ROOT/'realistic-dirt/textures/blocks'
SIZE=512


def load(name):
    with Image.open(REF/name) as im:
        im=ImageOps.exif_transpose(im).convert('RGB')
        if im.size != (1024,1024):raise ValueError(f'Unexpected source dimensions: {name}')
        return im.copy()


def fit(image,box):
    return image.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)


def make_shelf():
    wood=load('wood.jpg').crop((24,130,1000,910))
    shelf=load('shelf.jpg')
    # Atlas normalized to 32x32 and upscaled to 512x512 (16px per UV unit).
    atlas=Image.new('RGB',(SIZE,SIZE))
    def put(image,uv):
        box=tuple(v*16 for v in uv)
        atlas.paste(fit(image,box),box[:2])
    top=shelf.crop((24,110,1000,318))
    bottom=shelf.crop((24,708,1000,916))
    front=shelf.crop((24,318,1000,708))
    put(top,(0,0,16,4));put(front,(0,4,16,12));put(bottom,(0,12,16,16))
    put(wood,(16,0,32,16))
    # The four lower regions are the powered left/right/center/unconnected
    # faces. Remove end posts where shelves join, leaving inner dividers.
    def linked(keep_left,keep_right):
        img=front.copy()
        if not keep_left:img.paste(front.crop((110,0,210,390)),(0,0))
        if not keep_right:img.paste(front.crop((760,0,860,390)),(876,0))
        return img
    put(linked(True,False),(0,16,16,24))
    put(linked(False,True),(16,16,32,24))
    put(linked(False,False),(0,24,16,32))
    put(linked(True,True),(16,24,32,32))
    return atlas


def make_pot():
    photo=load('pot.jpg')
    atlas=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
    # The vanilla 16x16 pot uses UV (5..11, 5..11) for its rim and
    # (5..11, 10..16) for its sides, sharing one row. Keep the 4x4 centre
    # transparent, matching the original top opening; the hole isn't a plant.
    scale=32
    rim=photo.crop((19,13,484,466)).resize((6*scale,6*scale),Image.Resampling.LANCZOS).convert('RGBA')
    mask=Image.open(REF/'vanilla-flower-pot.png').convert('RGBA').getchannel('A')
    rim.putalpha(mask.crop((5,5,11,11)).resize((6*scale,6*scale),Image.Resampling.NEAREST))
    atlas.paste(rim,(5*scale,5*scale))
    side=photo.crop((205,480,815,1014)).resize((6*scale,6*scale),Image.Resampling.LANCZOS).convert('RGBA')
    atlas.paste(side,(5*scale,10*scale))
    return atlas


def main():
    for name,im in [('oak_shelf',make_shelf()),('flower_pot',make_pot())]:
        im.save(OUT/f'{name}.png',optimize=True)
        print(f'Prepared {name}: {im.size} {im.mode}')

if __name__=='__main__':main()
