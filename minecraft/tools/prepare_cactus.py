#!/usr/bin/env python3
"""Prepare the supplied cactus side and end photographs (Pillow required).

From repo root: python3 minecraft/tools/prepare_cactus.py
The opaque images are fitted into the vanilla cactus' transparent inset.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path('minecraft')
SIDE_SOURCE = ROOT / 'cactus-reference/side.jpg'
END_SOURCE = ROOT / 'cactus-reference/end.jpg'
BLOCKS = ROOT / 'realistic-dirt/textures/blocks'
SIDE_OUTPUT = BLOCKS / 'cactus_side.png'
END_OUTPUT = BLOCKS / 'cactus_top.png'
SIZE = 512
INSET = SIZE // 16
EDGE_BLEND = 24


def load_photo(path, size):
    with Image.open(path) as src:
        if src.size != (1024, 1024):
            raise ValueError(f'Expected 1024x1024 user photo: {path}')
        return ImageOps.fit(ImageOps.exif_transpose(src).convert('RGB'), size, Image.Resampling.LANCZOS)


def prepare_side(path=SIDE_SOURCE):
    width = SIZE - 2 * INSET
    photo = load_photo(path, (width, SIZE))
    # Soften only the vertical repeat along stacked cactus blocks. Crop from
    # unmodified source each time; the central material stays untouched.
    result = photo.copy()
    for d in range(EDGE_BLEND):
        t = 1 - d / EDGE_BLEND
        blend = .5 * t * t * (3 - 2*t)
        top = photo.crop((0, d, width, d + 1))
        bottom = photo.crop((0, SIZE-1-d, width, SIZE-d))
        result.paste(Image.blend(top, bottom, blend), (0, d))
        result.paste(Image.blend(bottom, top, blend), (0, SIZE-1-d))
    # Vanilla cactus-side texture reserves the outer 1/16 on each side as
    # transparency; its sparse pixel-spike silhouettes are not reproduced.
    rgba = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rgba.paste(result.convert('RGBA'), (INSET, 0))
    return rgba


def prepare_end(path=END_SOURCE):
    width = SIZE - 2 * INSET
    photo = load_photo(path, (width, width))
    rgba = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rgba.paste(photo.convert('RGBA'), (INSET, INSET))
    return rgba


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    prepare_side().save(SIDE_OUTPUT, optimize=True)
    prepare_end().save(END_OUTPUT, optimize=True)
    print(f'Prepared cactus side {SIDE_OUTPUT} and shared top/bottom {END_OUTPUT}')


if __name__ == '__main__':
    main()
