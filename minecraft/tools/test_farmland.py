#!/usr/bin/env python3
"""Regression checks for the farmland atlas mappings and processed PNGs.

Run from the repository root with Pillow installed:
    python minecraft/tools/test_farmland.py
These checks cannot replace a visual test in Minecraft.
"""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path('minecraft/realistic-dirt')
BLOCKS = ROOT / 'textures/blocks'


class FarmlandTests(unittest.TestCase):
    def test_vanilla_face_and_state_indices(self):
        faces = json.loads((ROOT / 'blocks.json').read_text(encoding='utf-8'))['farmland']
        self.assertEqual(faces['textures'], {
            'up': 'farmland', 'down': 'farmland_side', 'side': 'farmland_side'
        })
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        wet, dry = atlas['farmland']['textures']
        self.assertEqual([v['path'] for v in wet['variations']], [
            'textures/blocks/farmland_wet', 'textures/blocks/farmland_moist'
        ])
        self.assertTrue(all(v['weight'] > 0 for v in wet['variations']))
        self.assertEqual(dry, 'textures/blocks/farmland_dry')
        self.assertEqual(atlas['farmland_side']['textures'], 'textures/blocks/farmland_side')

    def test_dimensions_edges_and_distinct_images(self):
        images = {}
        for name in ('dry', 'moist', 'wet', 'side'):
            image = Image.open(BLOCKS / f'farmland_{name}.png')
            self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))
            # Opposite outermost pixels match after edge blending.
            self.assertIsNone(ImageChops.difference(image.crop((0, 0, 1, 512)),
                                                    image.crop((511, 0, 512, 512))).getbbox())
            self.assertIsNone(ImageChops.difference(image.crop((0, 0, 512, 1)),
                                                    image.crop((0, 511, 512, 512))).getbbox())
            images[name] = image.copy()
        for a, b in (('wet', 'moist'), ('dry', 'wet'), ('dry', 'moist')):
            self.assertIsNotNone(ImageChops.difference(images[a], images[b]).getbbox())
        # Both wet variants use a shared edge, reducing position-variant seams.
        for box in ((0, 0, 1, 512), (511, 0, 512, 512),
                    (0, 0, 512, 1), (0, 511, 512, 512)):
            self.assertIsNone(ImageChops.difference(images['wet'].crop(box),
                                                    images['moist'].crop(box)).getbbox())


if __name__ == '__main__':
    unittest.main()
