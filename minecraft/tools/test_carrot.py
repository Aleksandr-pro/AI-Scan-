#!/usr/bin/env python3
"""Check mature carrot crop preparation and archives, not in-game rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_carrot import SOURCE, OUTPUT, SIZE, GROUND_Y, prepare

ROOT = Path('minecraft/realistic-dirt')


class CarrotTests(unittest.TestCase):
    def test_source_and_crop_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '14a7df10a70e7db7a4fe74626d2df61ebdcd32a14df905ca4ea8b266cb1e9e67')
        self.assertEqual(GROUND_Y, 720)
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertGreater(alpha.histogram()[0], 100000)
            self.assertGreater(sum(alpha.histogram()[128:]), 50000)
            # The remaining shoulder/stems end at the soil plane.
            self.assertGreater(sum(alpha.crop((0, SIZE-4, SIZE, SIZE)).histogram()[128:]), 100)

    def test_vanilla_scope_and_distributables(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        # Bedrock's vanilla carrots array continues to select stages 0..3.
        self.assertNotIn('carrots', terrain)
        self.assertNotIn('carrots', blocks)
        self.assertFalse((ROOT / 'textures/items/carrot.png').exists())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 85, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 85, 0])
                self.assertEqual(archive.read('textures/blocks/carrots_stage_3.png'), OUTPUT.read_bytes())
                for stage in range(3):
                    path = f'textures/blocks/carrots_stage_{stage}.png'
                    self.assertEqual(archive.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/carrot.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
