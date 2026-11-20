#!/usr/bin/env python3
"""Extract the fern from a dark, nontransparent user JPG.

Run from repository root. Requires Pillow, numpy, and opencv-python-headless.
Matting is approximate; the original dark leaves/background overlap in color.
"""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path('minecraft')
SOURCE = ROOT / 'fern-reference/fern.jpg'
OUTPUT = ROOT / 'realistic-dirt/textures/blocks/fern.png'
SIZE = 512


def extract():
    with Image.open(SOURCE) as src:
        if src.size != (1080, 866):
            raise ValueError('Expected the user screenshot, 1080x866')
        rgb = np.asarray(ImageOps.exif_transpose(src).convert('RGB'))
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    mask = np.full(g.shape, cv2.GC_PR_BGD, np.uint8)
    background = (g < 34) | (g-b < 7) | (g-r < 2)
    foreground = (g > 65) & (g-r >= 6) & (g-b > 23)
    possible = (g > 42) & (g-r >= 4) & (g-b >= 12)
    mask[possible] = cv2.GC_PR_FGD
    mask[background] = cv2.GC_BGD
    mask[foreground] = cv2.GC_FGD
    mask[:150, :] = cv2.GC_BGD
    mask[815:, :] = cv2.GC_BGD
    cv2.setRNGSeed(1729)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb[:, :, ::-1].copy(), mask, None, bg_model, fg_model, 4, cv2.GC_INIT_WITH_MASK)
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    alpha = cv2.GaussianBlur(binary, (3, 3), .5)
    rgba = np.dstack((rgb, alpha))
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, 'RGBA')


def prepare():
    plant = extract()
    bounds = plant.getchannel('A').point(lambda x: 255 if x > 100 else 0).getbbox()
    if not bounds:
        raise ValueError('No fern extracted')
    plant = plant.crop(bounds)
    # Full image fits a one-block plant without stretching its proportions.
    plant.thumbnail((SIZE - 8, SIZE - 8), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(plant, ((SIZE - plant.width)//2, SIZE - 4 - plant.height))
    return canvas


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared vanilla fern texture: {OUTPUT}')


if __name__ == '__main__':
    main()
