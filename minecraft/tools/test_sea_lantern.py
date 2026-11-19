#!/usr/bin/env python3
"""Check the sea lantern's vanilla atlas path and five-frame strip."""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path('minecraft/realistic-dirt')


class SeaLanternTests(unittest.TestCase):
    def test_atlas_and_flipbook_frames(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['sea_lantern']['textures'], 'textures/blocks/sea_lantern')
        with Image.open(ROOT / 'textures/blocks/sea_lantern.png') as strip:
            self.assertEqual((strip.mode, strip.size), ('RGB', (512, 2560)))
            first = strip.crop((0, 0, 512, 512))
            for i in range(1, 5):
                frame = strip.crop((0, i * 512, 512, (i + 1) * 512))
                self.assertIsNone(ImageChops.difference(first, frame).getbbox())
            # The photograph's centre is brighter than its framed corner.
            self.assertGreater(sum(first.getpixel((256, 256))), sum(first.getpixel((16, 16))))


if __name__ == '__main__':
    unittest.main()
