#!/usr/bin/env python3
"""Derive coloured pane-edge strips from the existing framed glass photos.

Main pane faces deliberately reuse the existing RGBA block texture, so the
photo, transparent centre and border match. The original JPEG's checkerboard
has already been removed by prepare_stained_glass.py. Requires Pillow.
"""
from pathlib import Path
from PIL import Image

BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
COLORS=('black','white','pink')


def main():
    for color in COLORS:
        with Image.open(BLOCKS/f'photo_stained_glass_{color}.png') as source:
            if source.size!=(256,256) or source.mode!='RGBA':
                raise ValueError(f'Unexpected source block texture: {color}')
            # Narrow upper frame, not the transparent centre. Stretch its depth
            # for the separate edge atlas slot used by Bedrock's pane geometry.
            edge=source.crop((0,2,256,8)).resize((256,256),Image.Resampling.BICUBIC)
            edge.save(BLOCKS/f'photo_stained_glass_{color}_pane_edge.png',optimize=True)
    print('Prepared black, white, and pink glass pane edge textures.')

if __name__=='__main__':main()
