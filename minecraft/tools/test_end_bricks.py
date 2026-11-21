#!/usr/bin/env python3
"""Verify end-brick material and packaging, not an in-game render test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_end_bricks import SOURCE, OUTPUT, SIZE, make_tile

ROOT=Path('minecraft/realistic-dirt')

class EndBrickTests(unittest.TestCase):
    def test_source_and_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '61eb080b2deb400a6adc1a0db168988e6b0b47114e262458b3c6d9d4eeb60054')
        with Image.open(OUTPUT) as img:
            self.assertEqual((img.mode,img.size),('RGB',(SIZE,SIZE)))
            self.assertEqual(img.tobytes(),make_tile().tobytes())
            self.assertEqual(img.getpixel((30,0)),img.getpixel((30,SIZE-1)))
            self.assertLess(sum(img.getpixel((20,0))),sum(img.getpixel((20,15))))
    def test_both_packages_and_scope(self):
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())
        self.assertEqual(terrain['texture_data']['end_bricks'],{'textures':'textures/blocks/end_bricks'})
        self.assertEqual(len(terrain['texture_data']['end_stone']['textures']['variations']),4)
        blocks=json.loads((ROOT/'blocks.json').read_text())
        self.assertNotIn('end_bricks',blocks)
        self.assertNotIn('end_stone',blocks)
        for name in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/name
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.read('textures/blocks/end_bricks.png'),OUTPUT.read_bytes())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json')),terrain)
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 4, 0])
                self.assertEqual(manifest['modules'][0]['version'],[2, 4, 0])
                for i in range(4):
                    n='end_stone'+(f'_variant_{i}' if i else '')+'.png'
                    self.assertEqual(z.read('textures/blocks/'+n),(ROOT/'textures/blocks'/n).read_bytes())

if __name__=='__main__':unittest.main()
