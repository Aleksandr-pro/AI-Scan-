#!/usr/bin/env python3
"""Prepare the five supplied crafting table photographs. Run from repo root.

Requires Pillow. Preserve the whole image, including its corner plates; the
slightly non-square inputs are resized to the square Bedrock face rather than
cropping off the frame. Bottom uses the game's existing crafting_table_bottom.
"""
from pathlib import Path
from PIL import Image, ImageOps

REFERENCE = Path('minecraft/crafting-table-reference')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
FACES = ('north', 'east', 'south', 'west', 'top')
SIZE = 512


def prepare(face):
    with Image.open(REFERENCE / f'{face}.jpg') as image:
        return ImageOps.exif_transpose(image).convert('RGB').resize(
            (SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for face in FACES:
        prepare(face).save(BLOCKS / f'photo_crafting_table_{face}.png', optimize=True)


if __name__ == '__main__':
    main()
