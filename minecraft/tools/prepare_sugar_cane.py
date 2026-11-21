#!/usr/bin/env python3
"""Prepare a single vertically repeatable sugar-cane texture for Bedrock.

Run from the repository root. Requires Pillow, numpy and scipy. Vanilla cane
stacks blocks using one texture, not age-indexed photo stages. Take the middle
of the last stalk cluster so repeated blocks do not each have a leafy crown;
soften the upper/lower seam. The item and block behaviour remain unchanged.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageOps

SOURCE = Path('minecraft/sugar-cane-reference/growth.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/reeds.tga')
SIZE = 512
CROP = (1050, 437, 1220, 607)
SEAM_BAND = 24


def soften_vertical_seam(image):
    # Blend the ends in premultiplied alpha, so stacked blocks share the same
    # edge pixels without a dark or white halo. Leaf fragments may still cut at
    # the seam; this cannot make independent vanilla block geometry continuous.
    p = np.asarray(image, dtype=np.float32) / 255
    p[:, :, :3] *= p[:, :, 3:4]
    for y in range(SEAM_BAND):
        weight = .5 * (1 - y / (SEAM_BAND-1))
        top, bottom = p[y].copy(), p[-1-y].copy()
        p[y] = top*(1-weight) + bottom*weight
        p[-1-y] = bottom*(1-weight) + top*weight
    alpha = p[:, :, 3:4]
    p[:, :, :3] = np.where(alpha > 0, p[:, :, :3] / np.maximum(alpha, 1/255), 0)
    return Image.fromarray(np.uint8(np.clip(np.rint(p*255), 0, 255)))


def prepare():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 843):
            raise ValueError('Expected the supplied 1264x843 JPG')
        rgb = np.asarray(image.crop(CROP), dtype=np.float32)
    # Remove white background and compensate for pale JPEG edges by borrowing
    # the nearest strongly coloured foreground pixel.
    alpha = np.clip((255-rgb.min(axis=2)-5)/28, 0, 1)
    color = np.clip((rgb - 255*(1-alpha[..., None])) / np.maximum(alpha[..., None], 1/255), 0, 255)
    solid = (alpha > .98) & (rgb.min(axis=2) < 150)
    if not np.any(solid):
        raise ValueError('No cane found')
    nearest = distance_transform_edt(~solid, return_distances=False, return_indices=True)
    nearest_rgb = rgb[nearest[0], nearest[1]]
    weight = np.clip((rgb.min(axis=2)-150)/60, 0, 1)[..., None]
    color = color*(1-weight) + nearest_rgb*weight
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    rgba[rgba[:, :, 3] == 0, :3] = 0
    section = Image.fromarray(rgba)
    width = round(section.width * SIZE / section.height)
    section = section.resize((width, SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(section, ((SIZE-width)//2, 0))
    return soften_vertical_seam(canvas)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT)
    print(f'Prepared repeatable vanilla sugar cane texture: {OUTPUT}')


if __name__ == '__main__':
    main()
