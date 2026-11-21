#!/usr/bin/env python3
"""Prepare a mature carrot crop from the supplied black-background photo.

Run from the repository root. Requires Pillow and numpy. The foliage and a
little carrot shoulder remain above the soil; the underground root is cropped.
Earlier crop stages and the carrot item are not modified.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE = Path('minecraft/carrot-reference/carrot.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/carrots_stage_3.png')
SIZE = 512
GROUND_Y = 720  # in the original 1024x1024 photograph


def prepare():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1024, 1024):
            raise ValueError('Expected the supplied 1024x1024 carrot photograph')
        rgb = np.asarray(image.crop((0, 0, 1024, GROUND_Y)), dtype=np.float32)
    # Fade the near-black backdrop and JPEG noise, preserving antialiased tips.
    alpha = np.clip((rgb.max(axis=2) - 5.0) / 24.0, 0.0, 1.0)
    # Remove the black backdrop's contribution from translucent edges.
    color = np.clip(rgb / np.maximum(alpha[..., None], 1.0 / 255.0), 0, 255)
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    rgba[rgba[..., 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    # Keep the photo's proportions and anchor the carrot at the soil surface.
    canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    canvas.paste(plant, (0, 1024 - GROUND_Y))
    return canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared mature carrot crop texture: {OUTPUT}')


if __name__ == '__main__':
    main()
