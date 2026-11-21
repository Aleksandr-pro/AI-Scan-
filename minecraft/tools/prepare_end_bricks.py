#!/usr/bin/env python3
"""Build a repeating end-stone-brick tile from the supplied masonry image.

One colour texture works without Vibrant Visuals. Each course has two bricks;
odd courses are offset by half a brick. No generated text or drawn objects.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

SOURCE = Path('minecraft/end-brick-reference/end-bricks.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/end_bricks.png')
SIZE = 256
# Source boxes include the natural relief, bevels and the photographed mortar.
BOXES = ((9,174,467,341), (478,174,891,341), (261,344,708,511),
         (80,516,493,684), (499,516,891,684), (341,688,708,852))


def make_tile():
    with Image.open(SOURCE) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
    if image.size != (1024,1024):
        raise ValueError('Unexpected source image dimensions')
    out = Image.new('RGB',(SIZE,SIZE),(44,43,32))
    # Integer row boundaries cover the full height without gaps. Wrap horizontal
    # bricks at both sides so staggered courses remain continuous across blocks.
    for row in range(6):
        y0 = round(row * SIZE / 6); y1 = round((row + 1) * SIZE / 6)
        for col in range(-1,3):
            x = col * 128 + (64 if row % 2 else 0)
            crop = image.crop(BOXES[(row*2+(col % 2)) % len(BOXES)])
            brick = crop.resize((128,y1-y0), Image.Resampling.LANCZOS)
            out.paste(brick,(x,y0))
    # Join exactly on the image boundary: the darker shared mortar makes
    # adjoining blocks meet rather than blending away the relief of the bricks.
    draw=ImageDraw.Draw(out)
    for row in range(6):
        y=round(row*SIZE/6)
        draw.line((0,y,SIZE-1,y),fill=(57,56,43),width=2)
    draw.line((0,SIZE-1,SIZE-1,SIZE-1),fill=(57,56,43))
    return out


def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    make_tile().save(OUTPUT,optimize=True)
    print(f'Wrote {OUTPUT}')


if __name__ == '__main__':
    main()
