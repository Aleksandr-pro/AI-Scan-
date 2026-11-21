#!/usr/bin/env python3
import io
import itertools
import json
from pathlib import Path
import unittest
import zipfile
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'grass-flow-experiment'
RP, BP = ADDON / 'resources', ADDON / 'behavior'

class GrassFlowTests(unittest.TestCase):
    def test_tiles_and_all_compatible_edges(self):
        # Edges depend only on shared vertices and the shared supertile phase;
        # match left/right and top/bottom even when the density changes.
        horizontal, vertical = {}, {}
        files = sorted((RP / 'textures/blocks').glob('grassflow_*.png'))
        tiles = [p for p in files if p.name != 'grassflow_dirt.png']
        self.assertEqual(len(tiles), 324)
        for path in tiles:
            vals = tuple(map(int, path.stem.removeprefix('grassflow_')))
            self.assertEqual(len(vals), 5)
            a = np.asarray(Image.open(path).convert('RGB'))
            self.assertEqual(a.shape, (128,128,3))
            nw, ne, sw, se, detail = vals
            px, pz = detail % 2, detail // 2
            for store, k, edge in [(horizontal,(nw,sw,px,pz),a[:,0]), (horizontal,(ne,se,(px+1)%2,pz),a[:,-1]),
                                    (vertical,(nw,ne,px,pz),a[0,:]), (vertical,(sw,se,px,(pz+1)%2),a[-1,:])]:
                if k in store:
                    np.testing.assert_array_equal(store[k], edge, err_msg=f'{path} edge {k}')
                else: store[k] = edge.copy()
        self.assertEqual(len(horizontal), 36)
        self.assertEqual(len(vertical), 36)
        p0 = np.asarray(Image.open(RP / 'textures/blocks/grassflow_11110.png'))
        p1 = np.asarray(Image.open(RP / 'textures/blocks/grassflow_11111.png'))
        self.assertGreater(np.mean(np.abs(p0.astype(float) - p1)), 1)

    def test_manifest_blocks_and_atlas(self):
        bp = json.loads((BP / 'manifest.json').read_text())
        rp = json.loads((RP / 'manifest.json').read_text())
        self.assertIn({'uuid':rp['header']['uuid'],'version':rp['header']['version']},bp['dependencies'])
        self.assertIn({'module_name':'@minecraft/server','version':'2.8.0'},bp['dependencies'])
        block = json.loads((BP / 'blocks/sample.json').read_text())['minecraft:block']
        self.assertEqual(block['description']['identifier'], 'grassflow:sample')
        self.assertEqual(len(block['permutations']), 324)
        states = block['description']['states']
        self.assertEqual(len(states), 5)
        self.assertEqual(np.prod([len(v) for v in states.values()]),324)
        atlas = json.loads((RP / 'textures/terrain_texture.json').read_text())['texture_data']
        self.assertEqual(len(atlas), 325)
        for entry in atlas.values():
            self.assertTrue((RP / (entry['textures']+'.png')).is_file())
        used = set()
        for perm in block['permutations']:
            up = perm['components']['minecraft:material_instances']['up']
            self.assertNotIn('tint_method', up)
            self.assertIn(up['texture'], atlas)
            used.add(up['texture'])
        self.assertEqual(len(used), 324)
        self.assertFalse((RP / 'biomes').exists())
        self.assertFalse((RP / 'textures/colormap').exists())

    def test_package_integrity(self):
        with zipfile.ZipFile(ROOT / 'grass-flow-experiment.mcaddon') as addon:
            self.assertIsNone(addon.testzip())
            self.assertEqual(set(addon.namelist()), {'grass-flow-resources.mcpack','grass-flow-behavior.mcpack'})
            for name, folder in [('grass-flow-resources.mcpack',RP),('grass-flow-behavior.mcpack',BP)]:
                with zipfile.ZipFile(io.BytesIO(addon.read(name))) as pack:
                    self.assertIsNone(pack.testzip())
                    files = {p.relative_to(folder).as_posix():p for p in folder.rglob('*') if p.is_file()}
                    self.assertEqual(set(files), set(pack.namelist()))
                    for filename, path in files.items():
                        self.assertEqual(pack.read(filename),path.read_bytes())

if __name__ == '__main__': unittest.main()
