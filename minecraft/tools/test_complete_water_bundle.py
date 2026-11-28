#!/usr/bin/env python3
"""Test integrated water, all prior assets and compatibility, not game rendering."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from PIL import Image
from build_complete_water_bundle import (ROOT,OLD_BUNDLE,WATER,COMPAT,OUTPUT,VERSION,RP,BP,
    WATER_TEXTURES,validate_water_and_compat,updated_manifest,extract,build)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.digest()

class CompleteWaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.tmp=tempfile.TemporaryDirectory(prefix='water-bundle-test-');root=Path(cls.tmp.name)
        cls.paths={}
        for label,path in [('old',OLD_BUNDLE),('new',OUTPUT)]:
            with zipfile.ZipFile(path) as outer:
                assert outer.testzip() is None and set(outer.namelist())=={RP,BP}
                for member in (RP,BP):
                    dest=root/(label+'-'+member);extract(outer,member,dest);cls.paths[label,member]=dest

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_resources_and_water_compatibility(self):
        with zipfile.ZipFile(self.paths['old',RP]) as old, zipfile.ZipFile(self.paths['new',RP]) as new,zipfile.ZipFile(WATER) as water,zipfile.ZipFile(COMPAT) as compat:
            self.assertIsNone(new.testzip());self.assertEqual(len(new.namelist()),len(set(new.namelist())))
            additions,overlap=validate_water_and_compat(old,water,compat)
            self.assertEqual(len(overlap),9);self.assertEqual(len(additions),90)
            self.assertEqual(set(new.namelist()),set(old.namelist())|set(additions))
            self.assertEqual(json.loads(new.read('manifest.json')),json.loads(updated_manifest(old.read('manifest.json'),'rp')))
            for name in set(old.namelist())-overlap-{'manifest.json'}:
                self.assertEqual(old.read(name),new.read(name),name)
            for name,data in additions.items():self.assertEqual(data,new.read(name),name)
            for name in overlap:
                bc=json.loads(old.read(name))['minecraft:client_biome']['components']
                wc=json.loads(water.read(name))['minecraft:client_biome']['components']
                actual=json.loads(new.read(name))['minecraft:client_biome']['components']
                self.assertEqual(actual['minecraft:grass_appearance'],bc['minecraft:grass_appearance'])
                self.assertEqual(actual['minecraft:water_appearance'],wc['minecraft:water_appearance'])
            for name,dim,alpha in [('textures/blocks/water_still_grey.png',(256,4096),230),('textures/blocks/water_flow_grey.png',(512,8192),240)]:
                with Image.open(io.BytesIO(new.read(name))) as im:
                    self.assertEqual((im.mode,im.size),('RGBA',dim))
                    self.assertEqual(im.getchannel('A').getextrema(),(alpha,alpha))
            self.assertIn('textures/blocks/ice.png',new.namelist())
            self.assertIn('textures/models/armor/elytra.png',new.namelist())
            self.assertIn('textures/entity/shield.png',new.namelist())
            raw=(ROOT/'catalog-source/bedrock-1.26.30.5/vanilla-terrain.json').read_text(encoding='utf-8-sig')
            atlas=json.loads('\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//')))['texture_data']
            self.assertEqual(atlas['flowing_water_grey']['textures'],'textures/blocks/water_flow_grey')
            self.assertEqual(atlas['still_water_grey']['textures'],'textures/blocks/water_still_grey')

    def test_behavior_unchanged_and_version_dependency(self):
        with zipfile.ZipFile(self.paths['old',BP]) as old,zipfile.ZipFile(self.paths['new',BP]) as new:
            self.assertIsNone(new.testzip());self.assertEqual(set(old.namelist()),set(new.namelist()))
            manifest=json.loads(new.read('manifest.json'))
            self.assertEqual(manifest,json.loads(updated_manifest(old.read('manifest.json'),'bp')))
            self.assertEqual(manifest['header']['version'],VERSION)
            for name in set(old.namelist())-{'manifest.json'}:self.assertEqual(old.read(name),new.read(name),name)

    def test_reject_tampered_compat(self):
        with zipfile.ZipFile(self.paths['old',RP]) as old,zipfile.ZipFile(WATER) as water,zipfile.ZipFile(COMPAT) as compat:
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w') as wrong:
                for name in compat.namelist():
                    data=compat.read(name)
                    if name.startswith('biomes/'):
                        obj=json.loads(data);obj['minecraft:client_biome']['components']['minecraft:grass_appearance']['color']='#FF0000';data=json.dumps(obj).encode()
                    wrong.writestr(name,data)
            with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as wrong:
                with self.assertRaises(ValueError):validate_water_and_compat(old,water,wrong)

    def test_reproducible(self):
        before=sha(OUTPUT);build();self.assertEqual(before,sha(OUTPUT))

if __name__=='__main__':unittest.main()
