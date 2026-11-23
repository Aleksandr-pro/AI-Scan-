#!/usr/bin/env python3
"""Prepare a repeating stripped-oak side from the user's photo; needs Pillow.

No rotation: wood grain follows the long axis of a vanilla vertical log.
This replaces the side texture only; the end grain is untouched.
"""
from pathlib import Path
from PIL import Image, ImageOps
from prepare_mud_concrete import match_edges

SOURCE=Path('minecraft/stripped-oak-reference/side.jpg')
OUTPUT=Path('minecraft/realistic-dirt/textures/blocks/stripped_oak_log.png')


def main():
    with Image.open(SOURCE) as source:
        image=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (512,512), Image.Resampling.LANCZOS)
    # Join the photo itself near its boundary; the central grain is unmodified.
    match_edges(image, 16).save(OUTPUT,optimize=True)
    print(f'Prepared {OUTPUT}: 512x512 RGB')

if __name__=='__main__':main()
