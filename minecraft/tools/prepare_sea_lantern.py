#!/usr/bin/env python3
"""Prepare a sea lantern from a supplied photograph using the vanilla flipbook layout.

From the repository root, with Pillow installed:
    python minecraft/tools/prepare_sea_lantern.py path/to/image.jpg
The source photograph is not included in the pack.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/sea_lantern.png')
FRAME_SIZE = 512
FRAMES = 5  # Vanilla Bedrock sea_lantern flipbook has five square frames.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    with Image.open(args.source) as source:
        frame = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),
                             (FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)
    # Keep the image's bevel and border intact instead of blending its edges.
    # Identical frames make a static image while keeping vanilla flipbook UVs.
    strip = Image.new('RGB', (FRAME_SIZE, FRAME_SIZE * FRAMES))
    for index in range(FRAMES):
        strip.paste(frame, (0, index * FRAME_SIZE))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    strip.save(OUTPUT, optimize=True)
    print(f'Saved {OUTPUT}: {strip.width}x{strip.height}, {FRAMES} identical frames')


if __name__ == '__main__':
    main()
