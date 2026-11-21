#!/usr/bin/env python3
"""Check the large combined bundle against both source packs, including versions."""
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'realistic-complete-grassflow.mcaddon'


class BundleTests(unittest.TestCase):
    def test_bundle(self):
        with zipfile.ZipFile(BUNDLE) as bundle, zipfile.ZipFile(ROOT/'grass-flow-experiment.mcaddon') as old_flow:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(set(bundle.namelist()), {'realistic-dirt.mcpack','grass-flow-resources.mcpack','grass-flow-behavior.mcpack'})
            sources = {'realistic-dirt.mcpack': ROOT/'realistic-dirt.mcpack',
                       'grass-flow-resources.mcpack': io.BytesIO(old_flow.read('grass-flow-resources.mcpack')),
                       'grass-flow-behavior.mcpack': io.BytesIO(old_flow.read('grass-flow-behavior.mcpack'))}
            manifests = {}
            for name, source in sources.items():
                with bundle.open(name) as raw, zipfile.ZipFile(io.BytesIO(raw.read())) as packaged, zipfile.ZipFile(source) as original:
                    self.assertIsNone(packaged.testzip())
                    self.assertEqual(set(packaged.namelist()), set(original.namelist()))
                    new_manifest = json.loads(packaged.read('manifest.json'))
                    old_manifest = json.loads(original.read('manifest.json'))
                    self.assertEqual(new_manifest['header']['uuid'], old_manifest['header']['uuid'])
                    for entry in packaged.namelist():
                        if entry != 'manifest.json':
                            self.assertEqual(packaged.read(entry), original.read(entry), f'{name}: {entry}')
                    for module in new_manifest['modules']:
                        self.assertEqual(module['version'], new_manifest['header']['version'])
                    manifests[name] = new_manifest
            base, resources, behavior = (manifests[n] for n in ('realistic-dirt.mcpack','grass-flow-resources.mcpack','grass-flow-behavior.mcpack'))
            self.assertEqual(base['header']['version'], [2, 6, 1])
            self.assertEqual(resources['header']['version'], [1, 0, 1])
            self.assertEqual(behavior['header']['version'], [1, 0, 1])
            self.assertIn({'uuid': resources['header']['uuid'], 'version': resources['header']['version']}, behavior['dependencies'])
            self.assertIn({'module_name':'@minecraft/server','version':'2.8.0'}, behavior['dependencies'])


if __name__ == '__main__': unittest.main()
