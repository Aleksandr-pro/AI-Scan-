#!/usr/bin/env python3
"""Static beetroot crop and archive checks; not a Minecraft rendering test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_beetroots import SOURCE, BLOCKS, SIZE, HEIGHTS, prepare_stage

ROOT = Path('minecraft/realistic-dirt')


class BeetrootTests(unittest.TestCase):
    def test_source_and_growth_textures(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'bc74a97b904de59b5cace0d9529daf576d50608bbf6c30ff6ecdb1d19140a5f3')
        hashes = []
        for stage in range(4):
            with Image.open(BLOCKS / f'beetroots_stage_{stage}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare_stage(stage).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertGreater(alpha.histogram()[0], 180000)
                self.assertGreater(sum(alpha.histogram()[128:]), 7000)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE-bbox[1], HEIGHTS[stage]-3)
                self.assertLessEqual(SIZE-bbox[1], HEIGHTS[stage])
                pixels = np.asarray(image).astype(int)
                red = (pixels[:,:,0] > pixels[:,:,1] * 1.3) & (pixels[:,:,0] > 45) & (pixels[:,:,3] > 128)
                self.assertGreater(red.sum(), 500)
                hashes.append(hashlib.sha256(image.tobytes()).digest())
        self.assertEqual(len(set(hashes)), 4)

    def test_vanilla_scope_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('beetroot', terrain)
        self.assertNotIn('beetroot', blocks)
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 85, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 85, 0])
                for stage in range(4):
                    path = f'textures/blocks/beetroots_stage_{stage}.png'
                    self.assertEqual(archive.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/beetroot.png', archive.namelist())
                self.assertNotIn('textures/items/beetroot_seeds.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
