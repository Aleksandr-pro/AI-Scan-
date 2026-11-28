#!/usr/bin/env python3
"""Check ordinary ice photo, transparency and bundle mapping (not game rendering)."""
import argparse
import io
import json
from pathlib import Path
import tempfile
import shutil
import unittest
import zipfile
from PIL import Image, ImageOps
import prepare_ordinary_ice
from build_complete_snow_bundle import OUTPUT, BASE, ICE_FILE, BUNDLE_VERSION, png_semantic_content

ROOT=Path('minecraft')
BASELINE=None
VERSION=[2,7,11]


def vanilla(name):
    raw=(ROOT/'catalog-source/bedrock-1.26.30.5'/name).read_text(encoding='utf-8-sig')
    return json.loads('\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//')))


class OrdinaryIceTests(unittest.TestCase):
    def test_photo_and_alpha(self):
        with Image.open(prepare_ordinary_ice.OUTPUT) as image:
            self.assertEqual((image.mode,image.size),('RGBA',(1024,1024)))
            actual=image.copy()
        prepared=prepare_ordinary_ice.prepare()
        self.assertEqual(actual.tobytes(),prepared.tobytes())
        with Image.open(prepare_ordinary_ice.SOURCE) as source:
            expected=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),(1024,1024),Image.Resampling.LANCZOS)
            self.assertEqual(actual.convert('RGB').tobytes(),expected.tobytes(),'photographic RGB must not be quantized or altered')
        alpha=actual.getchannel('A'); low,high=alpha.getextrema()
        self.assertGreater(low,0);self.assertLess(high,255);self.assertGreater(high-low,20)
        center=alpha.crop((256,256,768,768))
        self.assertLess(sum(center.histogram()[128:]),1024*1024//4)  # many centre pixels transmit the view

    def test_original_vanilla_scope_and_installed_asset(self):
        atlas=vanilla('vanilla-terrain.json')['texture_data']
        blocks=vanilla('vanilla-blocks.json')
        self.assertEqual(atlas['ice']['textures'],'textures/blocks/ice')
        self.assertEqual(blocks['ice']['textures'],'ice')
        self.assertNotEqual(blocks['packed_ice']['textures'],'ice')
        self.assertNotEqual(blocks['frosted_ice']['textures'],'ice')
        self.assertNotEqual(atlas['blue_ice']['textures'],'textures/blocks/ice')
        self.assertEqual(prepare_ordinary_ice.MAIN_OUTPUT.read_bytes(),prepare_ordinary_ice.OUTPUT.read_bytes())
        with zipfile.ZipFile(BASE) as main:
            self.assertIsNone(main.testzip())
            self.assertLess(BASE.stat().st_size,100*1024*1024)
            self.assertEqual(main.read(ICE_FILE),prepare_ordinary_ice.OUTPUT.read_bytes())
            self.assertEqual(json.loads(main.read('textures/terrain_texture.json'))['texture_data']['ice'],{'textures':'textures/blocks/ice'})
            manifest=json.loads(main.read('manifest.json'))
            self.assertEqual(manifest['header']['version'],VERSION)
            self.assertTrue(all(m['version']==VERSION for m in manifest['modules']))
        with tempfile.TemporaryDirectory() as d, zipfile.ZipFile(OUTPUT) as outer:
            path=Path(d)/'resources.mcpack'
            with outer.open('realistic-snow-resources.mcpack') as src, path.open('wb') as dst:shutil.copyfileobj(src,dst)
            with zipfile.ZipFile(path) as rp:
                self.assertEqual(rp.read(ICE_FILE),prepare_ordinary_ice.OUTPUT.read_bytes())
                self.assertEqual(json.loads(rp.read('textures/terrain_texture.json'))['texture_data']['ice'],{'textures':'textures/blocks/ice'})
                self.assertEqual(json.loads(rp.read('manifest.json'))['header']['version'],BUNDLE_VERSION)

    def test_main_pack_preserves_v2710(self):
        if BASELINE is None:self.skipTest('pass --baseline /path/to/v2.7.10.mcpack')
        with zipfile.ZipFile(BASELINE) as old, zipfile.ZipFile(BASE) as new:
            self.assertEqual(set(new.namelist()),set(old.namelist()))
            self.assertNotEqual(old.read(ICE_FILE),new.read(ICE_FILE))
            for name in set(old.namelist())-{'manifest.json',ICE_FILE}:
                before,after=old.read(name),new.read(name)
                if before!=after:
                    self.assertTrue(name.endswith('.png'),name)
                    self.assertEqual(png_semantic_content(before),png_semantic_content(after),name)
            expected=json.loads(old.read('manifest.json'))
            expected['header']['version']=VERSION
            for m in expected['modules']:m['version']=VERSION
            self.assertEqual(json.loads(new.read('manifest.json')),expected)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path)
    args,rest=parser.parse_known_args();BASELINE=args.baseline
    unittest.main(argv=[__file__,*rest])
