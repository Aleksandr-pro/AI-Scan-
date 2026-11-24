#!/usr/bin/env python3
"""Prepare the user's copper-block face, including its photographic bevel.

Run from the repository root. Requires Pillow. This is a 512px colour texture,
not a physical 3D bevel or PBR material. No edge blending is used: the photo's
light top border and darker bottom border deliberately remain intact.
"""
from pathlib import Path
from PIL import Image, ImageOps

SOURCE = Path('minecraft/copper-block-reference/copper-block.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/copper_block.png')


def prepare():
    with Image.open(SOURCE) as source:
        return ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (512,512), Image.Resampling.LANCZOS)


def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    prepare().save(OUTPUT,optimize=True)
    print(f'Prepared {OUTPUT} with the original frame')

if __name__=='__main__':main()
