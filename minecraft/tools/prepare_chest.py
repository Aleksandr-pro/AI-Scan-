#!/usr/bin/env python3
"""Build the ordinary chest textures from the three supplied photographs.

Run from the repository root; requires Pillow. The 64x64/128x64 layout follows
Mojang's Bedrock 1.26.30.5 chest texture samples. One atlas unit is 16 pixels.
The moving lid is 5 units high and the body 10; the lock has its own cuboid.
"""
from pathlib import Path
from PIL import Image, ImageOps

REF = Path('minecraft/chest-reference')
ROOT = Path('minecraft/realistic-dirt')
SCALE = 16
RESAMPLE = Image.Resampling.LANCZOS


def load(name):
    with Image.open(REF / f'{name}.jpg') as im:
        return im.convert('RGB')


def widen(im):
    """Make a wide face without stretching the central lock or side bands.

    Stretch the two wooden fields separately; their joins are continuous at
    each cut. The wide chest has 30 model units instead of the single's 14.
    """
    w, h = im.size
    cuts = [0, round(w*.09), round(w*.32), round(w*.68), round(w*.91), w]
    new_w = round(w * 30 / 14)
    widths = [cuts[1], 0, cuts[3]-cuts[2], 0, w-cuts[4]]
    remaining = new_w - sum(widths)
    widths[1] = remaining // 2
    widths[3] = remaining - widths[1]
    result = Image.new('RGB', (new_w, h))
    x = 0
    for i, width in enumerate(widths):
        part = im.crop((cuts[i], 0, cuts[i+1], h)).resize((width, h), RESAMPLE)
        result.paste(part, (x, 0))
        x += width
    return result


def atlas(wide=False):
    front, side, top = (load(name) for name in ('front', 'side', 'top'))
    if wide:
        front, top = widen(front), widen(top)
    width = 30 if wide else 14
    im = Image.new('RGBA', ((128 if wide else 64)*SCALE, 64*SCALE), (30, 19, 14, 255))

    def put(img, x, y, w, h):
        im.paste(img.resize((w*SCALE, h*SCALE), RESAMPLE).convert('RGBA'), (x*SCALE, y*SCALE))

    # Standard cuboid UV net: left side, front, right side, back.
    # Split the photographed surfaces at the model's lid/body boundary,
    # preserving the continuous picture when the chest is closed.
    back = widen(side) if wide else side
    for image, x, w in ((side, 0, 14), (front, 14, width),
                         (ImageOps.mirror(side), 14+width, 14),
                         (back, 28+width, width)):
        y_split = round(image.height / 3)
        put(image.crop((0, 0, image.width, y_split)), x, 14, w, 5)
        put(image.crop((0, y_split, image.width, image.height)), x, 33, w, 10)
    # Top, underside of lid, inside body, and bottom of body.
    put(top, 14, 0, width, 14)
    put(ImageOps.flip(top), 14+width, 0, width, 14)
    put(top, 14, 19, width, 14)
    put(ImageOps.flip(top), 14+width, 19, width, 14)
    # The latch is a separate 2x4x1 cuboid (the first 6x5 atlas units).
    # Use the dark metal tab from the front photo, not a second keyhole.
    f = load('front')
    metal = f.crop((int(f.width*.44), int(f.height*.09), int(f.width*.56), int(f.height*.22)))
    for x, w in ((0, 1), (1, 2), (3, 1), (4, 2)):
        put(metal, x, 1, w, 4)
    put(metal, 1, 0, 2, 1)
    put(metal, 3, 0, 2, 1)
    return im


def main():
    entity = ROOT / 'textures/entity/chest'
    entity.mkdir(parents=True, exist_ok=True)
    for wide, name in ((False, 'normal'), (True, 'double_normal')):
        atlas(wide).save(entity / f'{name}.png', optimize=True)
    blocks = ROOT / 'textures/blocks'
    for name in ('front', 'side', 'top'):
        load(name).resize((512, 512), RESAMPLE).save(blocks / f'photo_chest_{name}.png', optimize=True)


if __name__ == '__main__':
    main()
