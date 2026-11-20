#!/usr/bin/env python3
"""Prepare the user's sand photo as a repeating 512px tile.

Run from the repository root: python minecraft/tools/prepare_sand.py
Requires Pillow. This only updates the ordinary sand texture.
"""
from pathlib import Path
from prepare_cobblestone import prepare

SOURCE = Path('minecraft/sand-reference/sand.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/sand.png')


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare(SOURCE).save(OUTPUT, optimize=True)
    print(f'Prepared tileable sand: {OUTPUT}')


if __name__ == '__main__':
    main()
