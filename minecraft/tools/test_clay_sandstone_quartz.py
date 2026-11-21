#!/usr/bin/env python3
"""Check mappings and texture assets for clay, sandstone and quartz."""
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path('minecraft/realistic-dirt')
ATLAS = {
    'clay': 'clay',
    'flattened_sandstone': 'sandstone_normal',
    'flattened_quartz_block_top': 'quartz_block_top',
    'flattened_quartz_block_side': 'quartz_block_side',
    'smooth_quartz': 'quartz_block_bottom',
    'quartz_bricks': 'quartz_bricks',
    'chiseled_quartz_block_top': 'quartz_block_chiseled',
    'chiseled_quartz_block_side': 'quartz_block_chiseled',
    'quartz_pillar_top': 'quartz_block_top',
    'quartz_pillar_side': 'quartz_block_lines',
}


def difference(first, second):
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3


class MaterialsTests(unittest.TestCase):
    def test_vanilla_paths_and_sandstone_faces(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        faces = json.loads((ROOT / 'blocks.json').read_text(encoding='utf-8'))['sandstone']
        self.assertEqual(faces['textures'], dict.fromkeys(('up', 'down', 'side'), 'flattened_sandstone'))
        self.assertFalse(faces['isotropic'])
        for key, name in ATLAS.items():
            with self.subTest(key=key):
                self.assertEqual(atlas[key]['textures'], f'textures/blocks/{name}')
                with Image.open(ROOT / f'textures/blocks/{name}.png') as image:
                    self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))
        caps = ['textures/blocks/'+name for name in ('quartz_block_top', 'quartz_block_chiseled', 'quartz_block_top', 'quartz_block_bottom')]
        self.assertEqual(atlas['quartz_block_top']['textures'], caps)
        self.assertEqual(atlas['quartz_block_bottom']['textures'], caps)
        self.assertEqual((ROOT/'textures/blocks/quartz_block_chiseled_top.png').read_bytes(), (ROOT/'textures/blocks/quartz_block_chiseled.png').read_bytes())
        # No aliases were installed for unrelated red/cut/chiseled sandstone.
        self.assertNotIn('flattened_redsandstone', atlas)
        self.assertNotIn('cut_sandstone', atlas)
        self.assertNotIn('chiseled_sandstone', atlas)

    def test_organic_tile_edges(self):
        for name in ('clay', 'sandstone_normal', 'quartz_block_side', 'quartz_block_bottom'):
            with self.subTest(name=name), Image.open(ROOT / f'textures/blocks/{name}.png') as image:
                x_seam = difference(image.crop((0, 0, 1, 512)), image.crop((511, 0, 512, 512)))
                y_seam = difference(image.crop((0, 0, 512, 1)), image.crop((0, 511, 512, 512)))
                x_detail = difference(image.crop((0, 0, 511, 512)), image.crop((1, 0, 512, 512)))
                y_detail = difference(image.crop((0, 0, 512, 511)), image.crop((0, 1, 512, 512)))
                self.assertLess(x_seam, x_detail * 1.5)
                self.assertLess(y_seam, y_detail * 1.5)

    def test_textures_are_distinct_and_pillar_cap_is_neutral(self):
        blocks = ROOT / 'textures/blocks'
        names = ('quartz_block_side', 'quartz_block_bottom', 'quartz_bricks',
                 'quartz_block_chiseled', 'quartz_block_lines')
        images = [Image.open(blocks / f'{name}.png') for name in names]
        for i, first in enumerate(images):
            for second in images[i + 1:]:
                self.assertIsNotNone(ImageChops.difference(first, second).getbbox())
        self.assertEqual((blocks / 'quartz_block_lines_top.png').read_bytes(),
                         (blocks / 'quartz_block_top.png').read_bytes())
        for image in images:
            image.close()


if __name__ == '__main__':
    unittest.main()
