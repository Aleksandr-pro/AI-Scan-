#!/usr/bin/env python3
"""Prepare the supplied clay, sandstone and five quartz images.

Run from the repository root, with Pillow installed:
    python minecraft/tools/prepare_clay_sandstone_quartz.py /path/to/photos
The original photographs are not included in the pack or repository.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

from prepare_cobblestone import prepare

BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = (512, 512)


def original_design(path):
    # Do not overlap opposite edges on designed patterns: that would ghost
    # the fluting, brick joints or the framed chiseled-quartz ornament.
    with Image.open(path) as source:
        return ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),
                            SIZE, Image.Resampling.LANCZOS)


def save(image, *names):
    for name in names:
        output = BLOCKS / f'{name}.png'
        image.save(output, optimize=True)
        print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir', type=Path)
    args = parser.parse_args()
    root = args.source_dir
    BLOCKS.mkdir(parents=True, exist_ok=True)

    # Organic surfaces: softly overlap photo margins to reduce tile seams.
    save(prepare(root / '1795102981802.jpg'), 'clay')
    # The original sandstone image was superseded by this newer photograph.
    save(prepare(root / '1795103623625.jpg'), 'sandstone_normal')
    normal = prepare(root / 'Кварц обычный.jpg')
    # Pillar end was not supplied: use neutral normal quartz, never the flutes.
    save(normal, 'quartz_block_side', 'quartz_block_top', 'quartz_block_lines_top')
    save(prepare(root / 'Кварц гладкий.jpg'), 'quartz_block_bottom')

    # Preserve the full pattern and orientation on the three designed tiles.
    save(original_design(root / 'Кварцевый кирпич.jpg'), 'quartz_bricks')
    save(original_design(root / 'Резной кварц.jpg'), 'quartz_block_chiseled', 'quartz_block_chiseled_top')
    save(original_design(root / 'Кварцевая колонна.jpg'), 'quartz_block_lines')


if __name__ == '__main__':
    main()
