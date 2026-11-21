#!/usr/bin/env python3
"""Static ordinary bush texture and archive checks; not in-game rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_bush import SOURCE, OUTPUT, SIZE, MAX_HEIGHT, prepare

ROOT = Path('minecraft/realistic-dirt')


class BushTests(unittest.TestCase):
    def test_source_and_transparency(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'a54f32b12de72d68fa72004ee2efb4a76a78afb582963a1bd2ee8c7a92497163')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertGreater(alpha.histogram()[0], 100000)
            self.assertGreater(sum(alpha.histogram()[128:]), 80000)
            bbox = alpha.getbbox()
            self.assertEqual(bbox[3], SIZE)
            self.assertLessEqual(SIZE-bbox[1], MAX_HEIGHT)
            self.assertGreater(sum(alpha.crop((0, SIZE-4, SIZE, SIZE)).histogram()[128:]), 25)

    def test_scope_and_distributables(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        # The vanilla atlas resolves bush.png; carried sprite remains separate.
        self.assertNotIn('bush', terrain)
        self.assertNotIn('bush', blocks)
        self.assertFalse((ROOT / 'textures/items/bush.png').exists())
        self.assertFalse((ROOT / 'textures/blocks/firefly_bush.png').exists())
        berry_paths = [f'textures/blocks/sweet_berry_bush_stage{i}.png' for i in range(4)]
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 91, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 91, 0])
                self.assertEqual(pack.read('textures/blocks/bush.png'), OUTPUT.read_bytes())
                self.assertNotIn('textures/items/bush.png', pack.namelist())
                self.assertNotIn('textures/blocks/firefly_bush.png', pack.namelist())
                for path in berry_paths:
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())


if __name__ == '__main__':
    unittest.main()
