#!/usr/bin/env python3
"""Validate glowstone and prismarine-brick assets and atlas mappings."""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path('minecraft/realistic-dirt')


def mean_difference(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


class GlowstonePrismarineTests(unittest.TestCase):
    def test_atlas_and_dimensions(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['glowstone']['textures'], 'textures/blocks/glowstone')
        self.assertEqual(atlas['prismarine_bricks']['textures'], 'textures/blocks/prismarine_bricks')
        self.assertEqual(atlas['prismarine_brick_slab']['textures'], 'textures/blocks/prismarine_bricks')
        # Never replace the legacy indexed array or rough/dark prismarine.
        for key in ('prismarine', 'flattened_prismarine', 'dark_prismarine'):
            self.assertNotIn(key, atlas)
        for name in ('glowstone', 'prismarine_bricks'):
            with self.subTest(name=name), Image.open(ROOT / f'textures/blocks/{name}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))

    def test_glowstone_edges(self):
        with Image.open(ROOT / 'textures/blocks/glowstone.png') as image:
            x_seam = mean_difference(image.crop((0, 0, 1, 512)), image.crop((511, 0, 512, 512)))
            y_seam = mean_difference(image.crop((0, 0, 512, 1)), image.crop((0, 511, 512, 512)))
            x_detail = mean_difference(image.crop((0, 0, 511, 512)), image.crop((1, 0, 512, 512)))
            y_detail = mean_difference(image.crop((0, 0, 512, 511)), image.crop((0, 1, 512, 512)))
            self.assertLess(x_seam, x_detail * 1.5)
            self.assertLess(y_seam, y_detail * 1.5)


if __name__ == '__main__':
    unittest.main()
