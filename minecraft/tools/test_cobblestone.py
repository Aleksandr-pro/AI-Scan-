#!/usr/bin/env python3
"""Check the cobblestone mapping and the processed repeating texture."""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path('minecraft/realistic-dirt')


def mean_difference(first, second):
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3


class CobblestoneTests(unittest.TestCase):
    def test_mapping_and_tile(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['cobblestone']['textures'], 'textures/blocks/cobblestone')
        image = Image.open(ROOT / 'textures/blocks/cobblestone.png')
        self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))
        # Seams should not jump more than typical adjacent pixels. This metric
        # cannot detect every visual artefact; an in-game check is still needed.
        x_seam = mean_difference(image.crop((0, 0, 1, 512)), image.crop((511, 0, 512, 512)))
        y_seam = mean_difference(image.crop((0, 0, 512, 1)), image.crop((0, 511, 512, 512)))
        x_detail = mean_difference(image.crop((0, 0, 511, 512)), image.crop((1, 0, 512, 512)))
        y_detail = mean_difference(image.crop((0, 0, 512, 511)), image.crop((0, 1, 512, 512)))
        self.assertLess(x_seam, x_detail * 1.2)
        self.assertLess(y_seam, y_detail * 1.2)
        self.assertGreater(x_detail, 5, 'Texture should retain photographic detail')


if __name__ == '__main__':
    unittest.main()
