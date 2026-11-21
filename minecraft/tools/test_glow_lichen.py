#!/usr/bin/env python3
"""Static checks of glow-lichen cutouts and packages, not a rendering test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_glow_lichen import SOURCE, BLOCKS, SIZE, BOXES, variant

ROOT = Path('minecraft/realistic-dirt')


def name(i):
    return 'glow_lichen' + (f'_variant_{i}' if i else '')


class GlowLichenTests(unittest.TestCase):
    def test_source_and_cutouts(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '460f539a758e14ad8654a0d1574de3d26d49a3b86aa0a6731286ad64ddfe3bbd')
        self.assertEqual(len(BOXES),3)
        hashes = set()
        for i in range(3):
            with Image.open(BLOCKS / (name(i)+'.png')) as im:
                self.assertEqual((im.mode,im.size),('RGBA',(SIZE,SIZE)))
                self.assertEqual(im.tobytes(),variant(i).tobytes())
                a = im.getchannel('A')
                self.assertEqual(a.getpixel((0,0)),0)
                self.assertGreater(a.histogram()[0],30000)
                self.assertGreater(sum(a.histogram()[128:]),10000)
                hashes.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(hashes),3)

    def test_atlas_and_packages(self):
        atlas = json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        self.assertEqual(atlas['glow_lichen']['textures']['variations'], [
            {'path':'textures/blocks/'+name(i), 'weight':1} for i in range(3)])
        self.assertNotIn('glow_lichen',json.loads((ROOT/'blocks.json').read_text()))
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path = Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[1,95,0])
                self.assertEqual(manifest['modules'][0]['version'],[1,95,0])
                self.assertEqual(json.loads(pack.read('textures/terrain_texture.json')),json.loads((ROOT/'textures/terrain_texture.json').read_text()))
                for i in range(3):
                    p = 'textures/blocks/'+name(i)+'.png'
                    self.assertEqual(pack.read(p),(ROOT/p).read_bytes())
                self.assertNotIn('textures/blocks/glow_lichen.texture_set.json', pack.namelist())
                self.assertNotIn('textures/blocks/glow_lichen_mers.tga', pack.namelist())


if __name__ == '__main__':
    unittest.main()
