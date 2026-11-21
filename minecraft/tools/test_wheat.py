#!/usr/bin/env python3
"""Check wheat photo preparation and archives, not in-game rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_wheat import SOURCE, OUTPUT, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class WheatTests(unittest.TestCase):
    def test_source_and_transparent_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '4cfe0558f77fb1ad53d8fcc83e234cfd5d1332e029ab34272105273021e4f7a1')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertGreater(alpha.histogram()[0], 50000)
            self.assertGreater(sum(alpha.histogram()[128:]), 100000)
            self.assertGreater(sum(alpha.crop((0, SIZE-4, SIZE, SIZE)).histogram()[128:]), 100)

    def test_vanilla_scope_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        # Do not replace the vanilla wheat array: it references stages 0..7.
        self.assertNotIn('wheat', terrain)
        self.assertNotIn('wheat', blocks)
        for stage in range(7):
            self.assertFalse((ROOT / f'textures/blocks/wheat_stage_{stage}.png').exists())
        self.assertFalse((ROOT / 'textures/items/wheat.png').exists())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as z:
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 76, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 76, 0])
                self.assertEqual(z.read('textures/blocks/wheat_stage_7.png'), OUTPUT.read_bytes())
                for stage in range(7):
                    self.assertNotIn(f'textures/blocks/wheat_stage_{stage}.png', z.namelist())
                self.assertNotIn('textures/items/wheat.png', z.namelist())


if __name__ == '__main__':
    unittest.main()
