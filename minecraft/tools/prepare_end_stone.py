#!/usr/bin/env python3
"""Four photographed end-stone textures and estimated PBR working maps.

Run from repo root. Requires Pillow, numpy, scipy. The ordinary pack uses only
albedo. A separate optional VV/PBR overlay uses normal + MER, not height+normal
simultaneously. Height and AO are reference maps, not physical measurements.
"""
from pathlib import Path
import io
import json
import zipfile
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageOps

ROOT = Path('minecraft')
SOURCE = ROOT/'end-stone-reference/end-stone.jpg'
BLOCKS = ROOT/'realistic-dirt/textures/blocks'
MAPS_ZIP = ROOT/'end-stone-material-maps.zip'
PBR_PACK = ROOT/'end-stone-pbr-optional.mcpack'
SIZE = 224
BOXES = ((19,23,304,308),(334,23,619,308),(647,23,932,308),(961,23,1246,308))


def name(i):
    return 'end_stone' + (f'_variant_{i}' if i else '')


def make_periodic(im, width=24):
    a = np.asarray(im,dtype=np.float32).copy()
    for axis in (1,0):
        src = a.copy()
        for d in range(width):
            w = .5*(1-d/(width-1))
            if axis == 1:
                a[:,d] = src[:,d]*(1-w) + src[:,-1-d]*w
                a[:,-1-d] = src[:,-1-d]*(1-w) + src[:,d]*w
            else:
                a[d,:] = src[d,:]*(1-w) + src[-1-d,:]*w
                a[-1-d,:] = src[-1-d,:]*(1-w) + src[d,:]*w
    return Image.fromarray(np.rint(a).astype(np.uint8))


def colors():
    with Image.open(SOURCE) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        if image.size != (1264,325):
            raise ValueError('Unexpected end-stone image')
        crops = [image.crop(box).resize((SIZE,SIZE),Image.Resampling.LANCZOS) for box in BOXES]
    base = make_periodic(crops[0])
    x,y=np.meshgrid(np.arange(SIZE),np.arange(SIZE))
    dist=np.minimum.reduce([x,y,SIZE-1-x,SIZE-1-y])
    fade=np.clip((dist-12)/28,0,1); fade=fade*fade*(3-2*fade)
    mask=Image.fromarray(np.rint(fade*255).astype(np.uint8))
    return [base]+[Image.composite(crop,base,mask) for crop in crops[1:]]


def maps(image):
    rgb=np.asarray(image,dtype=np.float32)/255
    lum=rgb[:,:,0]*.2126+rgb[:,:,1]*.7152+rgb[:,:,2]*.0722
    # Hypothesis only: low luminance corresponds to a recess. Shadows and
    # baked highlights are not measured height and may invert actual geometry.
    h=np.clip(.5+1.2*(gaussian_filter(lum,1,mode='wrap')-.45),0,1)
    dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))*2.0
    dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))*2.0
    normal=np.stack((-dx,dy,np.ones_like(h)),axis=2)
    normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    normals=np.rint((normal*.5+.5)*255).clip(0,255).astype(np.uint8)
    rough=np.clip(.89-.12*(h-.5),.76,.97)
    ao=np.clip(.78+.22*h,0,1)
    conv=lambda a: Image.fromarray(np.rint(a*255).clip(0,255).astype(np.uint8))
    # MER: red metalness 0, green emissivity 0, blue roughness.
    mer=np.zeros((SIZE,SIZE,3),dtype=np.uint8);mer[:,:,2]=np.rint(rough*255).astype(np.uint8)
    return {'albedo':image,'normal':Image.fromarray(normals),'height':conv(h),
            'roughness':conv(rough),'ao':conv(ao),'mer':Image.fromarray(mer)}


def png(image):
    buf=io.BytesIO();image.save(buf,format='PNG',optimize=True);return buf.getvalue()


def main():
    BLOCKS.mkdir(parents=True,exist_ok=True)
    variants=colors()
    generated=[maps(im) for im in variants]
    for i,images in enumerate(generated):
        (BLOCKS/(name(i)+'.png')).write_bytes(png(images['albedo']))
    notes=('Estimated material maps from a single image, not measured geometry.\n'
           'Albedo is used by the classic pack. Normal and MER are used only by the optional PBR overlay.\n'
           'Height and AO are reference maps; neither creates real geometry or works in Classic.\n'
           'Do not specify normal and heightmap together in a Bedrock texture set.\n')
    with zipfile.ZipFile(MAPS_ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.txt',notes)
        for i,images in enumerate(generated):
            for layer,im in images.items():
                z.writestr(f'variant_{i}/{layer}.png',png(im))
    manifest={'format_version':2,'header':{'name':'End Stone — optional PBR',
        'description':'Approximate normals and roughness for four end-stone variants; VV only',
        'uuid':'2783de60-19ab-484e-8f60-027f759e5f5a','version':[1,0,0],
        'min_engine_version':[1,21,120]},'modules':[{'type':'resources',
        'uuid':'33515669-9e31-4d3c-b19b-465e8b2a160c','version':[1,0,0]}],
        'capabilities':['pbr']}
    atlas={'resource_pack_name':'optional_end_stone_pbr','texture_name':'atlas.terrain',
           'texture_data':{'end_stone':{'textures':{'variations':[
               {'path':'textures/blocks/'+name(i),'weight':1} for i in range(4)]}}}}
    with zipfile.ZipFile(PBR_PACK,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        z.writestr('textures/terrain_texture.json',json.dumps(atlas,indent=2)+'\n')
        for i,images in enumerate(generated):
            n=name(i);directory='textures/blocks/'
            z.writestr(directory+n+'.png',png(images['albedo']))
            z.writestr(directory+n+'_normal.png',png(images['normal']))
            z.writestr(directory+n+'_mer.png',png(images['mer']))
            descriptor={'format_version':'1.16.100','minecraft:texture_set':{
                'color':n, 'normal':n+'_normal', 'metalness_emissive_roughness':n+'_mer'}}
            z.writestr(directory+n+'.texture_set.json',json.dumps(descriptor,indent=2)+'\n')
    print('Prepared four classic end-stone variations, estimated maps and optional PBR overlay.')


if __name__ == '__main__':
    main()
