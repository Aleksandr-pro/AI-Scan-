#!/usr/bin/env python3
"""Check ordinary ice photo, transparency and bundle mapping (not game rendering)."""
import io
import json
from pathlib import Path
import tempfile
import shutil
import unittest
import zipfile
from PIL import Image, ImageOps
import prepare_ordinary_ice
from build_complete_snow_bundle import OUTPUT, ICE_FILE, BUNDLE_VERSION

ROOT=Path('minecraft')


def vanilla(name):
    raw=(ROOT/'catalog-source/bedrock-1.26.30.5'/name).read_text(encoding='utf-8-sig')
    return json.loads('\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//')))


class OrdinaryIceTests(unittest.TestCase):
    def test_photo_and_alpha(self):
        with Image.open(prepare_ordinary_ice.OUTPUT) as image:
            self.assertEqual((image.mode,image.size),('RGBA',(512,512)))
            actual=image.copy()
        prepared=prepare_ordinary_ice.prepare()
        self.assertEqual(actual.tobytes(),prepared.tobytes())
        with Image.open(prepare_ordinary_ice.SOURCE) as source:
            expected=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),(512,512),Image.Resampling.LANCZOS)
            self.assertEqual(actual.convert('RGB').tobytes(),expected.tobytes(),'photographic RGB must not be quantized or altered')
        alpha=actual.getchannel('A'); low,high=alpha.getextrema()
        self.assertGreater(low,0);self.assertLess(high,255);self.assertGreater(high-low,20)
        center=alpha.crop((128,128,384,384))
        self.assertLess(sum(center.histogram()[128:]),512*512//4)  # many centre pixels transmit the view

    def test_original_vanilla_scope_and_installed_asset(self):
        atlas=vanilla('vanilla-terrain.json')['texture_data']
        blocks=vanilla('vanilla-blocks.json')
        self.assertEqual(atlas['ice']['textures'],'textures/blocks/ice')
        self.assertEqual(blocks['ice']['textures'],'ice')
        self.assertNotEqual(blocks['packed_ice']['textures'],'ice')
        self.assertNotEqual(blocks['frosted_ice']['textures'],'ice')
        self.assertNotEqual(atlas['blue_ice']['textures'],'textures/blocks/ice')
        with tempfile.TemporaryDirectory() as d, zipfile.ZipFile(OUTPUT) as outer:
            path=Path(d)/'resources.mcpack'
            with outer.open('realistic-snow-resources.mcpack') as src, path.open('wb') as dst:shutil.copyfileobj(src,dst)
            with zipfile.ZipFile(path) as rp:
                self.assertEqual(rp.read(ICE_FILE),prepare_ordinary_ice.OUTPUT.read_bytes())
                self.assertEqual(json.loads(rp.read('textures/terrain_texture.json'))['texture_data']['ice'],{'textures':'textures/blocks/ice'})
                self.assertEqual(json.loads(rp.read('manifest.json'))['header']['version'],BUNDLE_VERSION)

if __name__=='__main__':unittest.main()
