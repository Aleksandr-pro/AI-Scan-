#!/usr/bin/env python3
"""Static archive checks; Minecraft import and rendering require a real client."""
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
ADDON=ROOT/'minecraft/snow-footprints.mcaddon'

class AddonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ADDON.read_bytes()
        with zipfile.ZipFile(io.BytesIO(cls.original)) as outer:
            assert outer.testzip() is None
            assert set(outer.namelist()) == {'snow-footprints-resources.mcpack','snow-footprints-behavior.mcpack'}
            cls.packs={}
            for name in outer.namelist():
                with zipfile.ZipFile(io.BytesIO(outer.read(name))) as pack:
                    assert pack.testzip() is None
                    cls.packs[name]={file:pack.read(file) for file in pack.namelist()}
        cls.r=cls.packs['snow-footprints-resources.mcpack']
        cls.b=cls.packs['snow-footprints-behavior.mcpack']

    def test_reproducible_and_current(self):
        subprocess.run([sys.executable,str(ROOT/'minecraft/tools/build_snow_footprints.py')],check=True,capture_output=True)
        self.assertEqual(self.original,ADDON.read_bytes())
        for folder,pack in [('resources',self.r),('behavior',self.b)]:
            for path,data in pack.items():
                self.assertEqual(data,(ROOT/'minecraft/snow-footprints'/folder/path).read_bytes())

    def test_manifests_particle_and_png(self):
        r=json.loads(self.r['manifest.json']);b=json.loads(self.b['manifest.json'])
        for manifest in (r,b):
            self.assertEqual(manifest['header']['version'],[1,1,0])
            self.assertTrue(all(m['version']==[1,1,0] for m in manifest['modules']))
        self.assertIn({'uuid':r['header']['uuid'],'version':r['header']['version']},b['dependencies'])
        self.assertIn({'module_name':'@minecraft/server','version':'2.8.0'},b['dependencies'])
        self.assertIn('scripts/main.js',self.b)
        particle=json.loads(self.r['particles/footprint.json'])['particle_effect']
        self.assertEqual(particle['description']['identifier'],'aegis:snow_footprint')
        comp=particle['components']
        self.assertEqual(comp['minecraft:particle_lifetime_expression']['max_lifetime'],60)
        self.assertEqual(comp['minecraft:particle_appearance_billboard']['facing_camera_mode'],'emitter_transform_xz')
        self.assertEqual(comp['minecraft:particle_initial_spin']['rotation'],'variable.aegis_angle')
        png=self.r['textures/particle/aegis_snow_footprint.png']
        self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        width,height,bit_depth,color_type=struct.unpack('>IIBB',png[16:26])
        self.assertEqual((width,height,bit_depth,color_type),(256,512,8,6))

    def test_only_art_and_manifest_changed_from_previous_addon(self):
        baseline=os.environ.get('SNOW_FOOTPRINT_BASELINE')
        if not baseline:self.skipTest('set SNOW_FOOTPRINT_BASELINE to the previous addon')
        with zipfile.ZipFile(baseline) as old_outer:
            self.assertEqual(set(old_outer.namelist()),set(self.packs))
            for pack_name,new in self.packs.items():
                with zipfile.ZipFile(io.BytesIO(old_outer.read(pack_name))) as old:
                    self.assertEqual(set(old.namelist()),set(new))
                    for path in old.namelist():
                        if path == 'manifest.json':
                            previous=json.loads(old.read(path)); current=json.loads(new[path])
                            previous['header']['version']=[1,1,0]
                            for module in previous['modules']:module['version']=[1,1,0]
                            for dependency in previous.get('dependencies',[]):
                                if dependency.get('uuid')=='62554f75-26af-4261-9f58-fa2cb185cf97':
                                    dependency['version']=[1,1,0]
                            self.assertEqual(previous,current)
                        elif path == 'textures/particle/aegis_snow_footprint.png':
                            self.assertNotEqual(old.read(path),new[path])
                        else:
                            self.assertEqual(old.read(path),new[path],path)

    def test_logic_mock(self):
        subprocess.run(['node',str(ROOT/'minecraft/tools/test_snow_footprints.mjs')],check=True)
        for name in ('scripts/main.js','scripts/footsteps.js'):
            source=self.b[name].decode()
            for mutation in ('setPermutation(', 'setType(', 'setDynamicProperty(', 'spawnEntity('):
                self.assertNotIn(mutation,source)

if __name__=='__main__': unittest.main()
