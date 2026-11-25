#!/usr/bin/env python3
import io
import json
import sys
from pathlib import Path
import subprocess
import unittest
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'melon-experiment'
ADDON = ROOT/'realistic-melon-experiment.mcaddon'

class MelonExperimentTests(unittest.TestCase):
    def test_archive_matches_source_and_dependencies(self):
        dirs={'melon-resources.mcpack':'resources','melon-auto.mcpack':'behavior','melon-recovery.mcpack':'recovery'}
        with zipfile.ZipFile(ADDON) as addon:
            self.assertEqual(set(addon.namelist()),set(dirs))
            for name,directory in dirs.items():
                with zipfile.ZipFile(io.BytesIO(addon.read(name))) as z:
                    expected={p.relative_to(BASE/directory).as_posix():p.read_bytes() for p in (BASE/directory).rglob('*') if p.is_file()}
                    self.assertEqual(set(z.namelist()),set(expected))
                    for path, content in expected.items(): self.assertEqual(z.read(path),content)
        rp=json.loads((BASE/'resources/manifest.json').read_text())
        for d in ('behavior','recovery'):
            bp=json.loads((BASE/d/'manifest.json').read_text())
            self.assertIn({'uuid':rp['header']['uuid'],'version':rp['header']['version']},bp['dependencies'])
            self.assertIn({'module_name':'@minecraft/server','version':'2.8.0'},bp['dependencies'])
        self.assertEqual((BASE/'behavior/blocks/melon.json').read_bytes(),(BASE/'recovery/blocks/melon.json').read_bytes())

    def test_geometry_and_texture_are_bounded(self):
        geo=json.loads((BASE/'resources/models/blocks/melon.geo.json').read_text())['minecraft:geometry'][0]
        cubes=geo['bones'][0]['cubes']
        self.assertEqual(len(cubes),9)  # 8 fruit slices and a stem
        for c in cubes:
            self.assertTrue(all(n > 0 for n in c['size']))
            for i in range(3):
                lo = 0 if i==1 else -8
                hi = 16 if i==1 else 8
                self.assertGreaterEqual(c['origin'][i],lo)
                self.assertLessEqual(c['origin'][i]+c['size'][i],hi+.0001)
        with Image.open(BASE/'resources/textures/blocks/aimelon_fruit.png') as atlas:
            self.assertEqual(atlas.size,(256,256))
            self.assertEqual(atlas.mode,'RGBA')
            self.assertGreater(len(atlas.getcolors(65536)),10)
        with Image.open(ROOT/'melon-reference/generated-texture.png') as original:
            self.assertEqual(original.size,(64,64))
        self.assertTrue(json.loads((ROOT/'melon-reference/generated-mesh.json').read_text())['positions'])
        sys.path.insert(0, str(ROOT/'tools'))
        from build_melon_experiment import geometry_and_atlas
        regenerated_geo, regenerated_atlas = geometry_and_atlas()
        self.assertEqual(regenerated_geo, {'format_version': '1.12.0', 'minecraft:geometry': [geo]})
        with Image.open(BASE/'resources/textures/blocks/aimelon_fruit.png') as saved:
            self.assertEqual(saved.tobytes(), regenerated_atlas.tobytes())

    def test_scanner(self):
        subprocess.run(['node',str(ROOT/'tools/test_melon_scanner.mjs')],check=True)

if __name__=='__main__':unittest.main()
