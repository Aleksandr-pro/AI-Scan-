#!/usr/bin/env python3
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
AUTO=ROOT/'grass-flow-automatic.mcaddon'
COMPLETE=ROOT/'realistic-complete-automatic.mcaddon'
NAMES={'grass-flow-resources.mcpack','grass-flow-automatic.mcpack','grass-flow-restore.mcpack','grass-flow-resume.mcpack'}

class AutomaticPackTests(unittest.TestCase):
    def test_standalone_and_dependencies(self):
        with zipfile.ZipFile(AUTO) as addon:
            self.assertIsNone(addon.testzip())
            self.assertEqual(set(addon.namelist()),NAMES)
            manifests={}
            for name in NAMES:
                with zipfile.ZipFile(io.BytesIO(addon.read(name))) as inner:
                    self.assertIsNone(inner.testzip())
                    manifests[name]=json.loads(inner.read('manifest.json'))
                    if name=='grass-flow-automatic.mcpack':
                        block=json.loads(inner.read('blocks/auto_terrain.json'))['minecraft:block']
                        self.assertEqual(block['description']['identifier'],'grassflow:auto_terrain')
                        self.assertEqual(len(block['permutations']),324)
                        self.assertEqual(block['components']['minecraft:movable']['movement_type'],'immovable')
                        self.assertIn('scripts/automatic.js',inner.namelist())
                        self.assertNotIn(b'/scriptevent',inner.read('scripts/main.js'))
            version=[1,0,2]
            for m in manifests.values():
                self.assertEqual(m['header']['version'],version)
                self.assertEqual(m['header']['min_engine_version'],[1,26,30])
            rp=manifests['grass-flow-resources.mcpack']
            auto=manifests['grass-flow-automatic.mcpack']
            self.assertIn({'uuid':rp['header']['uuid'],'version':version},auto['dependencies'])
            for name in ['grass-flow-restore.mcpack','grass-flow-resume.mcpack']:
                self.assertIn({'uuid':auto['header']['uuid'],'version':version},manifests[name]['dependencies'])
            uuids=[m['header']['uuid'] for m in manifests.values()]
            self.assertEqual(len(uuids),len(set(uuids)))

    def test_original_resources_preserved(self):
        with zipfile.ZipFile(AUTO) as new, zipfile.ZipFile(ROOT/'grass-flow-experiment.mcaddon') as old:
            with zipfile.ZipFile(io.BytesIO(new.read('grass-flow-resources.mcpack'))) as a, zipfile.ZipFile(io.BytesIO(old.read('grass-flow-resources.mcpack'))) as b:
                self.assertEqual(set(a.namelist()),set(b.namelist()))
                for name in a.namelist():
                    if name!='manifest.json': self.assertEqual(a.read(name),b.read(name),name)

    def test_full_bundle(self):
        with zipfile.ZipFile(COMPLETE) as bundle, zipfile.ZipFile(AUTO) as addon:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(set(bundle.namelist()),NAMES | {'realistic-dirt.mcpack'})
            for name in NAMES: self.assertEqual(bundle.read(name),addon.read(name),name)
            with zipfile.ZipFile(io.BytesIO(bundle.read('realistic-dirt.mcpack'))) as combined, zipfile.ZipFile(ROOT/'realistic-dirt.mcpack') as source:
                self.assertIsNone(combined.testzip())
                self.assertEqual(set(combined.namelist()),set(source.namelist()))
                a,b=(json.loads(z.read('manifest.json')) for z in (combined,source))
                self.assertEqual(a['header']['uuid'],b['header']['uuid'])
                self.assertEqual(a['header']['version'],[2,6,1])
                for name in source.namelist():
                    if name!='manifest.json':self.assertEqual(combined.read(name),source.read(name),name)

if __name__=='__main__':unittest.main()
