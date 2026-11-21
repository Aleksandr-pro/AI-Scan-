#!/usr/bin/env python3
"""Extract the supplied mature wheat from its black JPEG background.

Run from the repository root. Requires Pillow and numpy. Only vanilla growth
stage 7 is replaced; all earlier stages and the wheat item are left alone.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE = Path('minecraft/wheat-reference/wheat.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/wheat_stage_7.png')
SIZE = 512


def prepare():
    with Image.open(SOURCE) as image:
        rgb = np.asarray(ImageOps.exif_transpose(image).convert('RGB'), dtype=np.float32)
    # The photograph's background is near-black, but JPEG creates a few dark
    # noisy pixels. Fade them out while retaining fine, brighter wheat awns.
    intensity = rgb.max(axis=2)
    alpha = np.clip((intensity - 5.0) / 24.0, 0.0, 1.0)
    # Undo black premultiplication at translucent borders to limit dark halos.
    color = np.clip(rgb / np.maximum(alpha[..., None], 1.0 / 255.0), 0, 255)
    pixels = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    pixels[pixels[..., 3] == 0, :3] = 0
    # Pillow resizes RGBA in premultiplied alpha, preserving fine edges.
    return Image.fromarray(pixels).resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared mature wheat texture: {OUTPUT}')


if __name__ == '__main__':
    main()
