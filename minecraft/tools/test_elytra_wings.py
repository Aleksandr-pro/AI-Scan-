#!/usr/bin/env python3
"""Validate elytra paths, UV atlas, existing assets and bundle; not game rendering."""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile
from PIL import Image
from build_complete_snow_bundle import BASE, OUTPUT, png_semantic_content

ROOT=Path('minecraft')
REF=ROOT/'elytra-reference'
PATHS={'textures/models/armor/elytra.png','textures/items/elytra.png','textures/items/broken_elytra.png'}
BASELINE=None

class ElytraTests(unittest.TestCase):
    def test_vanilla_paths_and_geometry(self):
        attach=json.loads((REF/'vanilla-elytra-attachable.json').read_text())['minecraft:attachable']['description']
        self.assertEqual(attach['textures']['default'],'textures/models/armor/elytra')
        self.assertEqual(attach['geometry']['default'],'geometry.elytra')
        geo=json.loads((REF/'vanilla-elytra-geometry.json').read_text())['geometry.elytra']
        self.assertEqual((geo['texturewidth'],geo['textureheight']),(64,32))
        bones={x['name']:x for x in geo['bones']}
        self.assertTrue(bones['right_wing']['mirror'])
        for wing in ('left_wing','right_wing'):
            cube=bones[wing]['cubes'][0]
            self.assertEqual(cube['size'],[10,20,2]);self.assertEqual(cube['uv'],[22,0])
        raw=(ROOT/'catalog-source/bedrock-1.26.30.5/vanilla-item-texture.json').read_text(encoding='utf-8-sig')
        atlas=json.loads('\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//')))['texture_data']
        self.assertEqual(atlas['elytra']['textures'],['textures/items/elytra','textures/items/broken_elytra'])

    def test_pack_and_bundle(self):
        with zipfile.ZipFile(BASE) as main, zipfile.ZipFile(OUTPUT) as outer:
            self.assertIsNone(main.testzip());self.assertLess(BASE.stat().st_size,100*1024*1024)
            manifest=json.loads(main.read('manifest.json'))
            self.assertEqual(manifest['header']['version'],[2,7,10])
            self.assertEqual(manifest['header']['uuid'],'c82fb06e-bbe1-4f64-b6aa-c3136b61a026')
            with zipfile.ZipFile(io.BytesIO(outer.read('realistic-snow-resources.mcpack'))) as bundle:
                for name in PATHS:
                    data=main.read(name)
                    self.assertEqual(data,(ROOT/'realistic-dirt'/name).read_bytes())
                    self.assertEqual(data,bundle.read(name))
                    with Image.open(io.BytesIO(data)) as im:
                        self.assertEqual(im.mode,'RGBA')
                        self.assertEqual(im.size,(1024,512) if '/models/' in name else (256,256))
                        self.assertEqual(im.getchannel('A').getextrema(),(0,255))
                        if '/models/' in name:
                            for box in ((24,2,34,22),(36,2,46,22)):
                                scaled=tuple(v*16 for v in box)
                                self.assertGreater(im.getchannel('A').crop(scaled).getbbox()[2],0)
                self.assertEqual(main.read('textures/blocks/ice.png'),(ROOT/'ice-reference/ice.png').read_bytes())
            self.assertNotEqual(main.read('textures/items/elytra.png'),main.read('textures/items/broken_elytra.png'))

    def test_previous_pack_preserved(self):
        if BASELINE is None:self.skipTest('pass --baseline /path/to/v2.7.8.mcpack')
        with zipfile.ZipFile(BASELINE) as old, zipfile.ZipFile(BASE) as new:
            self.assertEqual(set(new.namelist()),set(old.namelist())|PATHS|{'textures/entity/shield.png'})
            previous=json.loads(old.read('manifest.json'))
            previous['header']['version']=[2,7,10]
            for m in previous['modules']:m['version']=[2,7,10]
            self.assertEqual(json.loads(new.read('manifest.json')),previous)
            for name in set(old.namelist())-{'manifest.json'}:
                a,b=old.read(name),new.read(name)
                if a!=b:
                    self.assertTrue(name.endswith('.png'),name)
                    self.assertEqual(png_semantic_content(a),png_semantic_content(b),name)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path)
    args,rest=parser.parse_known_args();BASELINE=args.baseline
    unittest.main(argv=[__file__,*rest])
