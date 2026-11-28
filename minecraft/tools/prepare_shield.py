#!/usr/bin/env python3
"""Place the supplied front, back and edge artwork into the vanilla shield UV.

Run from the repository root with Pillow 13.0.0. Shape cutouts are approximate;
the original cuboid model, protruding grip, animation and patterned-shield
handling are not changed. Pixel/alpha display in Bedrock is not verified.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

REF=Path('minecraft/shield-reference')
OUT=Path('minecraft/realistic-dirt/textures/entity/shield.png')
S=8  # 64x64 vanilla atlas -> 512x512


def masked_crop(image, box, polygon):
    crop=image.crop(box).convert('RGBA')
    mask=Image.new('L',image.size)
    ImageDraw.Draw(mask).polygon(polygon,fill=255)
    crop.putalpha(mask.crop(box))
    return crop


def make():
    image=ImageOps.exif_transpose(Image.open(REF/'shield-reference.jpg')).convert('RGB')
    # Trace the supplied image's exterior, removing the dark background. The
    # points are hand-selected, not additional shield geometry.
    front=masked_crop(image,(80,10,540,808),[(84,78),(158,48),(184,50),(256,31),(313,11),(367,31),(441,49),(465,47),(534,78),(534,680),(477,733),(366,782),(313,806),(257,780),(143,731),(86,680)])
    back=masked_crop(image,(608,48,1059,774),[(611,66),(674,49),(1004,49),(1057,66),(1057,698),(1006,768),(664,768),(611,698)])
    front=front.resize((12*S,22*S),Image.Resampling.LANCZOS)
    back=back.resize((12*S,22*S),Image.Resampling.LANCZOS)
    atlas=Image.open(REF/'vanilla-shield.png').convert('RGBA').resize((64*S,64*S),Image.Resampling.NEAREST)
    # Cuboid [12,22,1], box UV [0,0]. North is back (1,1), south
    # is front (14,1); two 1-pixel side faces and top/bottom complete it.
    atlas.paste(back,(1*S,1*S))
    atlas.paste(front,(14*S,1*S))
    edge=image.crop((1140,40,1210,791)).resize((S,22*S),Image.Resampling.LANCZOS).convert('RGBA')
    atlas.paste(edge,(0,1*S));atlas.paste(edge,(13*S,1*S))
    metal=image.crop((90,72,530,96)).resize((12*S,S),Image.Resampling.LANCZOS).convert('RGBA')
    atlas.paste(metal,(1*S,0));atlas.paste(metal,(13*S,0))
    # Preserve the vanilla cube UV positions for the actual 3-D handle.
    grip=image.crop((700,290,746,515)).resize((6*S,6*S),Image.Resampling.LANCZOS).convert('RGBA')
    for x,w in [(26,6),(32,2),(34,6),(40,2)]:
        atlas.paste(grip.resize((w*S,6*S),Image.Resampling.LANCZOS),(x*S,6*S))
    atlas.paste(grip.resize((2*S,6*S),Image.Resampling.LANCZOS),(32*S,0))
    atlas.paste(grip.resize((2*S,6*S),Image.Resampling.LANCZOS),(34*S,0))
    return atlas


def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    make().save(OUT,optimize=True)
    print(OUT, OUT.stat().st_size,'bytes')

if __name__=='__main__':main()
