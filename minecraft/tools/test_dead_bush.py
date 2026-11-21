#!/usr/bin/env python3
"""Check dead bush texture preparation and archives, not in-game rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_dead_bush import SOURCE, OUTPUT, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class DeadBushTests(unittest.TestCase):
    def test_source_and_transparent_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '1d0567d788648d9bf762eaa7726ed195fc1ee262805373140d5389a6572d36d5')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertGreater(alpha.histogram()[0], 120000)
            self.assertGreater(sum(alpha.histogram()[128:]), 50000)
            self.assertEqual(alpha.getbbox()[3], SIZE)
            self.assertGreater(sum(alpha.crop((0, SIZE-4, SIZE, SIZE)).histogram()[128:]), 25)

    def test_scope_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('deadbush', terrain)
        self.assertNotIn('deadbush', blocks)
        self.assertFalse((ROOT / 'textures/blocks/deadbush.tga').exists())
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 97, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 97, 0])
                self.assertEqual(pack.read('textures/blocks/deadbush.png'), OUTPUT.read_bytes())
                self.assertEqual(pack.read('textures/blocks/bush.png'), (ROOT / 'textures/blocks/bush.png').read_bytes())
                for i in range(4):
                    path = f'textures/blocks/sweet_berry_bush_stage{i}.png'
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/blocks/deadbush.tga', pack.namelist())


if __name__ == '__main__':
    unittest.main()
