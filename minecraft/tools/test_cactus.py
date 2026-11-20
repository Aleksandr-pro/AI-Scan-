#!/usr/bin/env python3
"""Cactus image and pack checks; this does not render the block in game."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from prepare_cactus import (
    SIZE, INSET, EDGE_BLEND, SIDE_SOURCE, END_SOURCE, SIDE_OUTPUT, END_OUTPUT,
    load_photo, prepare_side, prepare_end,
)

ROOT = Path('minecraft/realistic-dirt')


def diff(a, b):
    mean = ImageStat.Stat(ImageChops.difference(a, b)).mean
    return sum(mean) / len(mean)


class CactusTests(unittest.TestCase):
    def test_sources_and_images(self):
        for source, checksum in (
            (SIDE_SOURCE, '6e9b8e9c2e77613e862f3db358e4ae902f8a022861a98d290f058fc5e0038ab0'),
            (END_SOURCE, '4fe1fa7f62b5310bd283e376b964373a42833502f1056d041c9039c73d2890b2'),
        ):
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), checksum)
            with Image.open(source) as original:
                self.assertEqual((original.mode, original.size), ('RGB', (1024, 1024)))
        with Image.open(SIDE_OUTPUT) as side, Image.open(END_OUTPUT) as end:
            self.assertEqual((side.mode, side.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual((end.mode, end.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(side.tobytes(), prepare_side().tobytes())
            self.assertEqual(end.tobytes(), prepare_end().tobytes())
            # Central side retains its own reference; only top/bottom rows are blended.
            side_content = side.crop((INSET, 0, SIZE-INSET, SIZE)).convert('RGB')
            side_photo = load_photo(SIDE_SOURCE, (SIZE-2*INSET, SIZE))
            rect = (0, EDGE_BLEND, SIZE-2*INSET, SIZE-EDGE_BLEND)
            self.assertEqual(side_content.crop(rect).tobytes(), side_photo.crop(rect).tobytes())
            end_content = end.crop((INSET, INSET, SIZE-INSET, SIZE-INSET)).convert('RGB')
            self.assertEqual(end_content.tobytes(), load_photo(END_SOURCE, (SIZE-2*INSET, SIZE-2*INSET)).tobytes())
            self.assertLess(diff(side_content.crop((0, 0, SIZE-2*INSET, 1)), side_content.crop((0, SIZE-1, SIZE-2*INSET, SIZE))), 1.5)
            side_alpha, end_alpha = side.getchannel('A'), end.getchannel('A')
            for crop in ((0, 0, INSET, SIZE), (SIZE-INSET, 0, SIZE, SIZE)):
                self.assertEqual(side_alpha.crop(crop).getextrema(), (0, 0))
            self.assertEqual(side_alpha.crop((INSET, 0, SIZE-INSET, SIZE)).getextrema(), (255, 255))
            for crop in ((0, 0, SIZE, INSET), (0, SIZE-INSET, SIZE, SIZE), (0, 0, INSET, SIZE), (SIZE-INSET, 0, SIZE, SIZE)):
                self.assertEqual(end_alpha.crop(crop).getextrema(), (0, 0))
            self.assertEqual(end_alpha.crop((INSET, INSET, SIZE-INSET, SIZE-INSET)).getextrema(), (255, 255))

    def test_atlas_and_archives(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        expected = {'cactus_side': 'textures/blocks/cactus_side', 'cactus_top': 'textures/blocks/cactus_top',
                    'cactus_bottom': 'textures/blocks/cactus_top'}
        for key, path in expected.items():
            self.assertEqual(atlas[key]['textures'], path)
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('cactus', blocks)  # inherit vanilla side/up/down mapping and sound
        self.assertNotIn('cactus_flower', blocks)
        self.assertFalse((ROOT / 'textures/blocks/cactus_bottom.png').exists())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertGreaterEqual(manifest['header']['version'], [1, 71, 0])
                self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
                for source in (SIDE_OUTPUT, END_OUTPUT):
                    self.assertEqual(archive.read(source.relative_to(ROOT).as_posix()), source.read_bytes())
                terrain = json.loads(archive.read('textures/terrain_texture.json'))['texture_data']
                for key in expected:
                    self.assertEqual(terrain[key], atlas[key])
                self.assertNotIn('textures/blocks/cactus_bottom.png', archive.namelist())
                self.assertNotIn('textures/blocks/cactus_flower.png', archive.namelist())
                self.assertNotIn('cactus-reference/side.jpg', archive.namelist())


if __name__ == '__main__':
    unittest.main()
