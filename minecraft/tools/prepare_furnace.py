#!/usr/bin/env python3
"""Prepare the supplied furnace body, lit front and unlit front images.

Run from the repo root with Pillow. Vanilla furnace has static front textures;
the engine selects the lit or unlit image according to furnace state.
"""
from pathlib import Path
from PIL import Image, ImageOps

REFERENCE = Path('minecraft/furnace-reference')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
FACES = ('body','front_on','front_off')
SIZE = 256


def prepare(face):
    if face not in FACES:
        raise ValueError(f'Unknown furnace face: {face}')
    with Image.open(REFERENCE / f'{face}.jpg') as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        if image.size != (1024,1024):
            raise ValueError('Expected the supplied square 1024x1024 photographs')
        return image.resize((SIZE,SIZE),Image.Resampling.LANCZOS)


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    for face in FACES:
        prepare(face).save(BLOCKS / f'photo_furnace_{face}.png', optimize=True)
    print('Prepared body and lit/unlit fronts for the furnace.')


if __name__ == '__main__':
    main()
