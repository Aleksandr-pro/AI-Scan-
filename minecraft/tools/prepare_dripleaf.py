#!/usr/bin/env python3
"""Photographic colours for Bedrock dripleaf's existing UV/alpha layouts.

Run from the repo root. Requires Pillow and numpy. Masks were transcribed from
Mojang's Bedrock samples v1.26.30.5. Nothing alters models or tilt behavior.
"""
from pathlib import Path
from PIL import Image, ImageOps
from dripleaf_masks import MASKS

SOURCE = Path('minecraft/dripleaf-reference/dripleaf.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 256
LEAVES = ((250,48,345,140), (510,205,600,270),
          (535,580,640,657), (785,65,875,155))
STEM = (190,390,210,470)


def load():
    with Image.open(SOURCE) as source:
        im = ImageOps.exif_transpose(source).convert('RGB')
        if im.size != (1264,848):
            raise ValueError('Unexpected dripleaf source')
        return im.copy()


def texture(name, leaf_index=0):
    source = load()
    rows = MASKS[name]
    if len(rows) != 16 or any(len(row) != 16 for row in rows):
        raise ValueError(f'Invalid UV mask for {name}')
    alpha = Image.new('L', (16,16))
    alpha.putdata([255 if c == '#' else 0 for row in rows for c in row])
    # Keep exact occupied UV regions; interpolation only softens their edges.
    alpha = alpha.resize((SIZE,SIZE), Image.Resampling.BILINEAR)
    coords = Image.new('L', (16,16)); coords.putdata([255 if c == '#' else 0 for row in rows for c in row])
    x0,y0,x1,y1 = coords.getbbox()
    region = (x0*16,y0*16,x1*16,y1*16)
    photo = source.crop(STEM if 'stem' in name else LEAVES[leaf_index])
    photo = photo.resize((region[2]-region[0],region[3]-region[1]), Image.Resampling.LANCZOS)
    rgb = Image.new('RGB', (SIZE,SIZE), (0,0,0))
    rgb.paste(photo, (region[0],region[1]))
    # Do not create partially visible black pixels outside the photo rectangle.
    # The bilinear mask is clipped to the vanilla occupied bounding region.
    clipped = Image.new('L', (SIZE,SIZE)); clipped.paste(alpha.crop(region), (region[0],region[1]))
    rgb.putalpha(clipped)
    return rgb


def textures():
    result = {name: texture(name) for name in MASKS}
    for kind in ('big_dripleaf_top','small_dripleaf_top'):
        for i in range(1,len(LEAVES)):
            result[f'{kind}_variant_{i}'] = texture(kind,i)
    return result


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for name, image in textures().items():
        image.save(BLOCKS / f'{name}.png', optimize=True)
    print('Prepared big and small dripleaf textures and four leaf-top variants.')


if __name__ == '__main__':
    main()
