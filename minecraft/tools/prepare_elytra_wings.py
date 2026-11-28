#!/usr/bin/env python3
"""Adapt the supplied image to Bedrock's mirrored vanilla elytra UV and icons.

Requires Pillow, numpy and opencv-python-headless. The white JPEG background is
estimated and removed; anti-aliased edges and smoke may render differently in
Minecraft's alpha-tested elytra material. No geometry or animation is changed.
"""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

REF=Path('minecraft/elytra-reference')
SOURCE=REF/'elytra-reference.jpg'
ROOT=Path('minecraft/realistic-dirt')
WORN=ROOT/'textures/models/armor/elytra.png'
ITEM=ROOT/'textures/items/elytra.png'
BROKEN=ROOT/'textures/items/broken_elytra.png'
SCALE=16  # a 64x32 vanilla texture becomes 1024x512


def cut_out():
    with Image.open(SOURCE) as src:
        img=ImageOps.exif_transpose(src).convert('RGB')
    rgb=np.array(img,dtype=np.uint8)
    low=rgb.min(axis=2); high=rgb.max(axis=2)
    # Only near-white regions connected to the picture border are treated as
    # background; isolated bright metallic highlights are retained.
    white=((low>=235) & ((high.astype(np.int16)-low)<=18)).astype(np.uint8)
    count,labels=cv2.connectedComponents(white,connectivity=8)
    border=np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])))
    border=border[border!=0]
    background=np.isin(labels,border) if count>1 else np.zeros(low.shape,bool)
    dist=cv2.distanceTransform((~background).astype(np.uint8),cv2.DIST_L2,3)
    edge=np.clip((255.0-low.astype(np.float32))/48.0,0,1)
    alpha=np.where(background,0,np.where(dist<6,edge,1)).astype(np.float32)
    # Remove the white matte at the antialiased border before downsizing.
    a=alpha[...,None]
    dematted=np.where(a>0.001,(rgb.astype(np.float32)-255*(1-a))/np.maximum(a,0.001),0)
    rgba=np.empty((*low.shape,4),dtype=np.uint8)
    rgba[:,:,:3]=np.clip(dematted,0,255).astype(np.uint8)
    rgba[:,:,3]=np.rint(alpha*255).astype(np.uint8)
    return Image.fromarray(rgba,'RGBA')


def produce():
    art=cut_out()
    # left wing on the supplied image: root on the right, tip on the left.
    # Vanilla uses the same UV region for both wings; the second is mirrored.
    left=art.crop((110,8,650,754)).resize((10*SCALE,20*SCALE),Image.Resampling.LANCZOS)
    atlas=Image.new('RGBA',(64*SCALE,32*SCALE))
    atlas.paste(left,(24*SCALE,2*SCALE))              # front: 24,2 -> 34,22
    atlas.paste(ImageOps.mirror(left),(36*SCALE,2*SCALE)) # back: 36,2 -> 46,22
    atlas.paste(left.crop((0,0,2,20*SCALE)).resize((2*SCALE,20*SCALE)),(22*SCALE,2*SCALE))
    atlas.paste(left.crop((10*SCALE-2,0,10*SCALE,20*SCALE)).resize((2*SCALE,20*SCALE)),(34*SCALE,2*SCALE))
    atlas.paste(left.crop((0,0,10*SCALE,2)).resize((10*SCALE,2*SCALE)),(24*SCALE,0))
    atlas.paste(left.crop((0,20*SCALE-2,10*SCALE,20*SCALE)).resize((10*SCALE,2*SCALE)),(34*SCALE,0))
    icon=Image.new('RGBA',(256,256))
    pair=ImageOps.contain(art.crop((95,8,1270,754)),(240,235),Image.Resampling.LANCZOS)
    icon.alpha_composite(pair,((256-pair.width)//2,(256-pair.height)//2))
    # The broken inventory icon is a visibly dimmer copy with a small split;
    # it is not an alternate worn-wing material.
    broken=ImageEnhance.Brightness(icon).enhance(.68)
    mask=broken.getchannel('A'); draw=ImageDraw.Draw(mask)
    draw.polygon([(124,70),(132,70),(127,102),(138,121),(126,148),(132,181),(124,181),(118,148),(128,122),(117,102)],fill=0)
    broken.putalpha(mask)
    return atlas,icon,broken


def main():
    for path,image in zip((WORN,ITEM,BROKEN),produce()):
        path.parent.mkdir(parents=True,exist_ok=True)
        image.save(path,optimize=True)
        print(path,path.stat().st_size,'bytes')

if __name__=='__main__':main()
