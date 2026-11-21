#!/usr/bin/env python3
"""Prepare classic anvil textures in vanilla indexed damage order.

Run from repo root with Pillow and numpy. Damaged stages use subtle shading
inferred from Mojang Bedrock samples v1.26.30.5; not separate user photos.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

REFERENCE=Path('minecraft/anvil-reference')
BLOCKS=Path('minecraft/realistic-dirt/textures/blocks')
SIZE=256
LEFT=3*SIZE//16
RIGHT=13*SIZE//16


def photo(face):
    with Image.open(REFERENCE/f'{face}.jpg') as im:
        im=ImageOps.exif_transpose(im).convert('RGB')
        if im.size!=(1024,1024):raise ValueError('Unexpected anvil image')
        return im


def base():
    return photo('side').resize((SIZE,SIZE),Image.Resampling.LANCZOS)


def template(stage):
    with Image.open(REFERENCE/f'anvil_top_damaged_{stage}.png') as im:
        if im.size!=(16,16):raise ValueError('Unexpected vanilla damage map')
        return np.asarray(im.convert('RGB'),dtype=np.float32)[:,3:13].mean(axis=2)


def top(stage):
    if stage not in (0,1,2):raise ValueError('Unknown damage stage')
    im=photo('top').resize((RIGHT-LEFT,SIZE),Image.Resampling.LANCZOS)
    rgb=np.asarray(im,dtype=np.float32)
    if stage:
        difference=template(stage)-template(0)
        # Transfer relative vanilla damage shading as an approximation, with
        # interpolation rather than adding large blocky cracks to the photo.
        delta=Image.fromarray(difference,mode='F').resize((RIGHT-LEFT,SIZE),Image.Resampling.BICUBIC)
        factor=np.clip(1 + np.asarray(delta,dtype=np.float32)*.010,.72,1.18)
        rgb=np.clip(rgb*factor[:,:,None],0,255)
    opaque=Image.fromarray(np.rint(rgb).astype(np.uint8)).convert('RGBA')
    out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0));out.paste(opaque,(LEFT,0))
    return out


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    base().save(BLOCKS/'anvil_base.png',optimize=True)
    for i in range(3):top(i).save(BLOCKS/f'anvil_top_damaged_{i}.png',optimize=True)
    print('Prepared anvil base and three approximate wear-stage top textures.')


if __name__=='__main__':main()
