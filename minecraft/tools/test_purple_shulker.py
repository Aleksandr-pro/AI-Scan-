#!/usr/bin/env python3
"""Static shulker UV, source and package tests; not a Bedrock rendering test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_purple_shulker import REFERENCE, ROOT, ENTITY, ICON, SCALE, photo, textures


class PurpleShulkerTests(unittest.TestCase):
    def test_sources_and_uv_mapping(self):
        hashes={'body.jpg':'7696e1f273576ddbad5348a9fa9058ae8869b0ccb3ff3d9f0f771bc8dc587799',
                'top.jpg':'32b6d838dbb4d8898c5265a3fd132fd0c7a5885ffd30327eddee18557a3ac903',
                'vanilla-purple.png':'c2649541a86a8b4df519d33dffca24f856aca8082197ed1d55bde3d5f4f61529'}
        for name,digest in hashes.items():
            self.assertEqual(hashlib.sha256((REFERENCE/name).read_bytes()).hexdigest(),digest)
        atlas,icon=textures(); unit=16*SCALE
        with Image.open(ENTITY) as im:
            self.assertEqual((im.mode,im.size),('RGBA',(64*SCALE,64*SCALE)))
            self.assertEqual(im.tobytes(),atlas.tobytes())
            self.assertEqual(im.crop((16*SCALE,0,32*SCALE,16*SCALE)).tobytes(),photo('top',unit).convert('RGBA').tobytes())
            vanilla=Image.open(REFERENCE/'vanilla-purple.png').convert('RGBA').resize(im.size,Image.Resampling.NEAREST)
            self.assertEqual(im.crop((0,52*SCALE,64*SCALE,64*SCALE)).tobytes(),vanilla.crop((0,52*SCALE,64*SCALE,64*SCALE)).tobytes())
            body=photo('body',unit).convert('RGBA')
            for x in (0,16,32,48):
                self.assertEqual(im.crop((x*SCALE,16*SCALE,(x+16)*SCALE,28*SCALE)).tobytes(),body.crop((0,0,unit,12*SCALE)).tobytes())
                self.assertEqual(im.crop((x*SCALE,44*SCALE,(x+16)*SCALE,52*SCALE)).tobytes(),body.crop((0,8*SCALE,unit,16*SCALE)).tobytes())
        with Image.open(ICON) as im:
            self.assertEqual((im.mode,im.size),('RGB',(256,256)))
            self.assertEqual(im.tobytes(),icon.tobytes())

    def test_pack_preserves_scope_and_inputs(self):
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        self.assertNotIn('purple_shulker_box',terrain)
        self.assertNotIn('shulker_box_top',terrain)
        self.assertNotIn('purple_shulker_box',json.loads((ROOT/'blocks.json').read_text()))
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            file=Path('minecraft')/package
            self.assertLess(file.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(file) as z:
                self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 2, 0])
                self.assertEqual(manifest['modules'][0]['version'],[2, 2, 0])
                for path in (ENTITY,ICON):
                    self.assertEqual(z.read(path.relative_to(ROOT).as_posix()),path.read_bytes())
                self.assertNotIn('textures/entity/shulker/shulker_undyed.png',z.namelist())
                self.assertNotIn('textures/entity/shulker/shulker_blue.png',z.namelist())
                self.assertNotIn('textures/blocks/shulker_top_undyed.png',z.namelist())
                self.assertNotIn('entity/shulker.entity.json',z.namelist())
                self.assertNotIn('textures/blocks/grass_path_side_source.png',z.namelist())
                self.assertNotIn('textures/blocks/short_grass_variant_0.png',z.namelist())
                self.assertEqual(z.read('textures/blocks/tallgrass.png'),(ROOT/'textures/blocks/short_grass_variant_0.png').read_bytes())


if __name__=='__main__':
    unittest.main()
