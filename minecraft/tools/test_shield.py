#!/usr/bin/env python3
"""Verify shield UV and archive preservation; cannot test the Bedrock renderer."""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile
from PIL import Image
import prepare_shield
from build_complete_snow_bundle import BASE,OUTPUT,png_semantic_content

REF=Path('minecraft/shield-reference')
PATH='textures/entity/shield.png'
BASELINE=None
VERSION=[2,7,10]

class ShieldTests(unittest.TestCase):
    def test_vanilla_reference_paths_and_uv(self):
        attach=json.loads((REF/'vanilla-shield.entity.json').read_text())['minecraft:attachable']['description']
        self.assertEqual(attach['textures']['default'],'textures/entity/shield')
        self.assertEqual(attach['geometry']['default'],'geometry.shield')
        geo=json.loads((REF/'vanilla-shield.geo.json').read_text())['minecraft:geometry'][0]
        self.assertEqual((geo['description']['texture_width'],geo['description']['texture_height']),(64,64))
        cubes=geo['bones'][0]['cubes']
        self.assertEqual([(c['size'],c['uv']) for c in cubes],[([2.0,6.0,6.0],[26,0]),([12.0,22.0,1.0],[0,0])])
        raw=Path('minecraft/catalog-source/bedrock-1.26.30.5/vanilla-item-texture.json').read_text(encoding='utf-8-sig')
        atlas=json.loads('\n'.join(x for x in raw.splitlines() if not x.lstrip().startswith('//')))['texture_data']
        self.assertEqual(atlas['shield']['textures'],'textures/entity/shield')

    def test_texture_and_archives(self):
        expected=prepare_shield.make()
        with Image.open(prepare_shield.OUT) as im:
            self.assertEqual((im.mode,im.size),('RGBA',(512,512)))
            self.assertEqual(im.tobytes(),expected.tobytes())
            for x in (1,14):
                face=im.crop((x*8,8,(x+12)*8,23*8))
                self.assertEqual(face.getchannel('A').getextrema(),(0,255))
        with zipfile.ZipFile(BASE) as main,zipfile.ZipFile(OUTPUT) as outer:
            self.assertIsNone(main.testzip());self.assertLess(BASE.stat().st_size,100*1024*1024)
            self.assertLess(OUTPUT.stat().st_size,100*1024*1024)
            self.assertEqual(main.read(PATH),prepare_shield.OUT.read_bytes())
            self.assertEqual(json.loads(main.read('manifest.json'))['header']['version'],VERSION)
            self.assertEqual(main.read('textures/blocks/ice.png'),Path('minecraft/ice-reference/ice.png').read_bytes())
            self.assertIn('textures/models/armor/elytra.png',main.namelist())
            with zipfile.ZipFile(io.BytesIO(outer.read('realistic-snow-resources.mcpack'))) as bundle:
                self.assertEqual(bundle.read(PATH),main.read(PATH))
                self.assertEqual(bundle.read('textures/models/armor/elytra.png'),main.read('textures/models/armor/elytra.png'))

    def test_all_previous_assets_preserved(self):
        if BASELINE is None:self.skipTest('pass --baseline /path/to/v2.7.9.mcpack')
        with zipfile.ZipFile(BASELINE) as old,zipfile.ZipFile(BASE) as new:
            self.assertEqual(set(new.namelist()),set(old.namelist())|{PATH})
            manifest=json.loads(old.read('manifest.json'))
            manifest['header']['version']=VERSION
            for module in manifest['modules']:module['version']=VERSION
            self.assertEqual(json.loads(new.read('manifest.json')),manifest)
            for name in set(old.namelist())-{'manifest.json'}:
                a,b=old.read(name),new.read(name)
                if a!=b:
                    self.assertTrue(name.endswith('.png'),name)
                    self.assertEqual(png_semantic_content(a),png_semantic_content(b),name)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path)
    args,rest=parser.parse_known_args();BASELINE=args.baseline
    unittest.main(argv=[__file__,*rest])
