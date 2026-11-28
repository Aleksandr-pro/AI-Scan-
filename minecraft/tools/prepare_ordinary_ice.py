#!/usr/bin/env python3
"""Prepare the supplied ordinary-ice photograph as a translucent 1024px tile.

The JPEG has no alpha channel: the smooth alpha is estimated, not measured.
Its bright perimeter and fine details are retained rather than tiled away.
Requires Pillow; run from the repository root. This changes no game materials.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

SOURCE=Path('minecraft/ice-reference/ice.jpg')
OUTPUT=Path('minecraft/ice-reference/ice.png')
MAIN_OUTPUT=Path('minecraft/realistic-dirt/textures/blocks/ice.png')
SIZE=1024


def prepare():
    with Image.open(SOURCE) as source:
        rgb=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),(SIZE,SIZE),Image.Resampling.LANCZOS)
    brightness=rgb.convert('L').filter(ImageFilter.GaussianBlur(SIZE/512))
    # Transmit the scene through the centre; slightly denser bright cracks and
    # the photographed outer rim. A 4-value step reduces PNG size, not RGB depth.
    alpha=Image.new('L',(SIZE,SIZE))
    src=brightness.load(); dst=alpha.load()
    rim_width=24*SIZE/512
    for y in range(SIZE):
        for x in range(SIZE):
            distance=min(x,y,SIZE-1-x,SIZE-1-y)
            rim=max(0,rim_width-distance)/rim_width
            value=max(110,min(180,112+(src[x,y]-110)*0.22+rim*28))
            dst[x,y]=int(value//4)*4
    result=rgb.convert('RGBA');result.putalpha(alpha)
    return result


def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    prepare().save(OUTPUT,optimize=True)
    MAIN_OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    MAIN_OUTPUT.write_bytes(OUTPUT.read_bytes())
    print(f'Prepared {OUTPUT} and {MAIN_OUTPUT} ({OUTPUT.stat().st_size} bytes)')

if __name__=='__main__':main()
