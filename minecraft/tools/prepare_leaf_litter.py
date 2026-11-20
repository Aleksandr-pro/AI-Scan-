#!/usr/bin/env python3
"""Remove the baked neutral checker from the user's leaf-litter JPG.

Requires Pillow, numpy and scipy. Run from repository root. Brown/grey edge
matting is approximate; very thin twigs may be lost or retain a slight fringe.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

SOURCE = Path('minecraft/leaf-litter-reference/source.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/leaf_litter.png')
COLORMAP = Path('minecraft/realistic-dirt/textures/colormap/dry_foliage.png')
SIZE = 512


def prepare(source=SOURCE):
    with Image.open(source) as image:
        if image.size != (1024, 1024):
            raise ValueError('Expected original 1024x1024 JPG')
        src = np.asarray(image.convert('RGB'), dtype=np.float32)
    r, g, b = (src[..., i] for i in range(3))
    chroma = r - b
    # High-confidence warm, relatively dark object pixels seed the matte.
    # Nearest seeds provide local edge color to avoid grey/white halos.
    seed = ((chroma >= 26) & (r - g >= 6) & (r < 205)) | (np.max(src, axis=2) < 155)
    distance, nearest = distance_transform_edt(~seed, return_indices=True)
    near_rgb = src[nearest[0], nearest[1]]
    near_chroma = np.maximum(near_rgb[..., 0] - near_rgb[..., 2], 12)
    alpha = np.clip((chroma - 3.0) / (near_chroma - 3.0), 0, 1)
    # Dark near-neutral details are actual material, not the 221/255 checker.
    alpha = np.where(np.max(src, axis=2) < 175, 1, alpha)
    alpha = np.where(seed, 1, alpha)
    alpha = np.where(distance <= 8, alpha, 0)
    # Use neighboring foreground colour for semitransparent edge pixels rather
    # than retaining the JPG's pale checker in those pixels.
    mix = np.clip((alpha - .85) / .15, 0, 1)[..., None]
    rgb = np.clip(src * mix + near_rgb * (1 - mix), 0, 255).astype(np.uint8)
    rgba = np.dstack((rgb, np.rint(alpha * 255).astype(np.uint8)))
    # Transparent pixel RGB is irrelevant to display; zero it for clean assets.
    rgba[rgba[..., 3] == 0, :3] = 0
    return Image.fromarray(rgba, 'RGBA').resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    # Try to preserve the supplied brown colours under vanilla dry-foliage
    # multiplication. Client-biome overrides can still impose other colours.
    # This affects any resource using the dry_foliage colormap, including mods.
    COLORMAP.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (256, 256), 'white').save(COLORMAP, optimize=True)
    print(f'Prepared transparent leaf litter: {OUTPUT}; neutral colormap: {COLORMAP}')


if __name__ == '__main__':
    main()
