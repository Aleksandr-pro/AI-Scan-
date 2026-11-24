#!/usr/bin/env python3
"""Prepare the supplied andesite photograph for full blocks and slabs.

Requires Pillow; execute from the repository root. The same unrotated 512px
colour texture is used by the natural block, slab, stair and wall vanilla
paths. Smooth cross-fades and matching edge pixels limit hard repeat seams.
"""
from pathlib import Path
from prepare_cobblestone import prepare
from prepare_mud_concrete import match_edges

SOURCE=Path('minecraft/andesite-reference/andesite.jpg')
OUTPUT=Path('minecraft/realistic-dirt/textures/blocks/stone_andesite.png')


def main():
    image=match_edges(prepare(SOURCE),4)
    image.save(OUTPUT,optimize=True)
    print(f'Prepared {OUTPUT}: {image.size} RGB')

if __name__=='__main__':main()
