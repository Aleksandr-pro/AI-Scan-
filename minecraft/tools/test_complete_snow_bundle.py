#!/usr/bin/env python3
"""Validate full/footprint bundle against the two published input archives.

Checks archive contents, dependency UUIDs, and deterministic rebuilds; it does
not test Minecraft import, activation, particle rendering, or performance.
"""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from build_complete_snow_bundle import (BASE, FOOTPRINTS, OUTPUT, LIMIT, RP_UUID,
    BP_UUID, BUNDLE_VERSION, RESOURCE_FILES, BEHAVIOR_FILES, bundle_manifest,
    behavior_manifest)


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.digest()

class CompleteBundleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='complete-snow-test-')
        cls.root=Path(cls.tmp.name)
        with zipfile.ZipFile(OUTPUT) as outer:
            assert len(outer.namelist())==2
            assert set(outer.namelist())=={'realistic-snow-resources.mcpack','realistic-snow-behavior.mcpack'}
            for name in outer.namelist():
                with outer.open(name) as source, (cls.root/name).open('wb') as dest:
                    shutil.copyfileobj(source,dest)
        cls.rp=cls.root/'realistic-snow-resources.mcpack'
        cls.bp=cls.root/'realistic-snow-behavior.mcpack'

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_base_is_preserved_and_footprints_integrated(self):
        self.assertLess(OUTPUT.stat().st_size,LIMIT)
        with zipfile.ZipFile(BASE) as base, zipfile.ZipFile(self.rp) as combined, zipfile.ZipFile(FOOTPRINTS) as addon:
            self.assertIsNone(combined.testzip())
            self.assertEqual(len(combined.namelist()),len(set(combined.namelist())))
            self.assertEqual(set(combined.namelist()),set(base.namelist())|RESOURCE_FILES)
            for name in base.namelist():
                if name=='manifest.json':
                    original=json.loads(base.read(name));actual=json.loads(combined.read(name))
                    self.assertEqual(actual,bundle_manifest(original))
                    self.assertNotEqual(actual['header']['uuid'],original['header']['uuid'])
                    self.assertEqual(actual['header']['min_engine_version'],[1,26,30])
                else:self.assertEqual(combined.read(name),base.read(name),name)
            with zipfile.ZipFile(io.BytesIO(addon.read('snow-footprints-resources.mcpack'))) as foot:
                for name in RESOURCE_FILES:self.assertEqual(combined.read(name),foot.read(name),name)

    def test_behavior_and_resource_dependency(self):
        with zipfile.ZipFile(self.bp) as combined, zipfile.ZipFile(FOOTPRINTS) as addon:
            self.assertIsNone(combined.testzip())
            self.assertEqual(set(combined.namelist()),BEHAVIOR_FILES)
            with zipfile.ZipFile(io.BytesIO(addon.read('snow-footprints-behavior.mcpack'))) as old:
                previous=json.loads(old.read('manifest.json')); manifest=json.loads(combined.read('manifest.json'))
                self.assertEqual(manifest,behavior_manifest(previous))
                self.assertNotEqual(manifest['header']['uuid'],previous['header']['uuid'])
                self.assertEqual(manifest['header']['uuid'],BP_UUID)
                self.assertEqual(manifest['header']['version'],BUNDLE_VERSION)
                self.assertTrue(all(m['version']==BUNDLE_VERSION for m in manifest['modules']))
                self.assertIn({'uuid':RP_UUID,'version':BUNDLE_VERSION},manifest['dependencies'])
                self.assertIn({'module_name':'@minecraft/server','version':'2.8.0'},manifest['dependencies'])
                for filename in ('scripts/main.js','scripts/footsteps.js'):
                    self.assertEqual(combined.read(filename),old.read(filename),filename)

    def test_rebuild_is_reproducible_and_fresh(self):
        previous=sha256(OUTPUT)
        subprocess.run([sys.executable,str(Path(__file__).with_name('build_complete_snow_bundle.py'))],check=True)
        if previous==sha256(OUTPUT):return
        # ZIP compression streams can differ with zlib versions even when the
        # actual files are identical. Compare all extracted member bytes.
        with zipfile.ZipFile(OUTPUT) as outer:
            for name in outer.namelist():
                rebuilt=self.root/('rebuilt-'+name)
                with outer.open(name) as source, rebuilt.open('wb') as dest:shutil.copyfileobj(source,dest)
                with zipfile.ZipFile(self.root/name) as before, zipfile.ZipFile(rebuilt) as after:
                    self.assertEqual(set(before.namelist()),set(after.namelist()))
                    for member in before.namelist():
                        self.assertEqual(before.read(member),after.read(member),f'{name}: {member}')

if __name__=='__main__':unittest.main()
