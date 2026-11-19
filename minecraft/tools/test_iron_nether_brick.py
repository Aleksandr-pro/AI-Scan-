#!/usr/bin/env python3
"""Regression checks for the iron block and ordinary nether-brick textures."""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path('minecraft/realistic-dirt')


class IronNetherBrickTests(unittest.TestCase):
    def test_atlas_and_images(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['iron_block']['textures'], 'textures/blocks/iron_block')
        for key in ('nether_brick', 'nether_brick_slab', 'nether_brick_wall'):
            self.assertEqual(atlas[key]['textures'], 'textures/blocks/nether_brick')
        for key in ('red_nether_brick', 'cracked_nether_bricks', 'chiseled_nether_bricks', 'raw_iron_block'):
            self.assertNotIn(key, atlas)
        for name in ('iron_block', 'nether_brick'):
            with self.subTest(name=name), Image.open(ROOT / f'textures/blocks/{name}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))
                self.assertGreater(sum(ImageStat.Stat(image).stddev), 20)

    def test_bricks_are_red_and_horizontal(self):
        with Image.open(ROOT / 'textures/blocks/nether_brick.png') as image:
            red, green, blue = ImageStat.Stat(image).mean
            self.assertGreater(red, green * 1.5)
            self.assertGreater(red, blue * 1.5)
            # Dark mortar crosses the image near each of the internal row joints.
            gray = image.convert('L')
            row = lambda y: ImageStat.Stat(gray.crop((0, y, 512, y + 1))).mean[0]
            for expected in (125, 255, 383):
                joint = min(row(y) for y in range(expected - 12, expected + 13))
                interior = row(expected + 40)
                self.assertLess(joint, interior)


if __name__ == '__main__':
    unittest.main()
