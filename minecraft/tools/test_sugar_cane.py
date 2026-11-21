#!/usr/bin/env python3
"""Static sugar cane texture and package checks; not a Minecraft test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_sugar_cane import SOURCE, OUTPUT, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class SugarCaneTests(unittest.TestCase):
    def test_source_and_repeatable_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'e04fff6dabe385fd01174984b215db4ad64ffdf26e244b47ec70b99a0cb01ac3')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size, image.format), ('RGBA', (SIZE, SIZE), 'TGA'))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            self.assertGreater(alpha.histogram()[0], 10000)
            self.assertGreater(sum(alpha.histogram()[128:]), 100000)
            self.assertEqual(image.crop((0, 0, SIZE, 1)).tobytes(),
                             image.crop((0, SIZE-1, SIZE, SIZE)).tobytes())

    def test_scope_and_distributables(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('reeds', terrain)
        self.assertNotIn('reeds', blocks)
        self.assertFalse((ROOT / 'textures/blocks/reeds.png').exists())
        self.assertFalse((ROOT / 'textures/items/reeds.png').exists())
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [2, 3, 0])
                self.assertEqual(manifest['modules'][0]['version'], [2, 3, 0])
                self.assertEqual(pack.read('textures/blocks/reeds.tga'), OUTPUT.read_bytes())
                self.assertNotIn('textures/blocks/reeds.png', pack.namelist())
                self.assertNotIn('textures/items/reeds.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
