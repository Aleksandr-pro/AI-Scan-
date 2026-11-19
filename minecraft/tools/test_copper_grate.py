#!/usr/bin/env python3
"""Regression checks for the copper grate's atlas entry and cutouts."""
import json
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path('minecraft/realistic-dirt')


class CopperGrateTests(unittest.TestCase):
    def test_grate_alpha_and_atlas(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['copper_grate']['textures'], 'textures/blocks/copper_grate')
        for other in ('exposed_copper_grate', 'weathered_copper_grate', 'oxidized_copper_grate'):
            self.assertNotIn(other, atlas)
        with Image.open(ROOT / 'textures/blocks/copper_grate.png') as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (512, 512)))
            alpha = image.getchannel('A')
            # All full and partial cells are open, not just black paint.
            for y in (110, 280, 450, 620, 790, 960):
                for x in (1, 150, 350, 555, 760, 970):
                    with self.subTest(x=x, y=y):
                        self.assertEqual(alpha.getpixel((x // 2, y // 2)), 0)
            # Retain copper rivets and cross-bars.
            for x, y in ((50, 20), (255, 20), (460, 190), (660, 360), (850, 700)):
                self.assertEqual(alpha.getpixel((x // 2, y // 2)), 255)
            histogram = alpha.histogram()
            self.assertGreater(histogram[0], 70000)
            self.assertGreater(histogram[255], 70000)


if __name__ == '__main__':
    unittest.main()
