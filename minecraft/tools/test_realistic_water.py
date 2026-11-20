#!/usr/bin/env python3
"""Validate water pack assets and references; not an in-game render test."""
import io
import json
import math
import unittest
import zipfile
from pathlib import Path
from uuid import UUID
from PIL import Image, ImageChops, ImageStat

ROOT = Path('minecraft')


class RealisticWaterTests(unittest.TestCase):
    def test_both_independent_packs(self):
        ids = []
        first_frames = {}
        for state in ('calm', 'rough'):
            source = ROOT / 'realistic-water' / state
            with zipfile.ZipFile(ROOT / f'realistic-water-{state}.mcpack') as archive:
                self.assertIsNone(archive.testzip())
                expected = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
                self.assertEqual(set(archive.namelist()), expected)
                for name in expected:
                    self.assertEqual(archive.read(name), (source / name).read_bytes())
                    if name.endswith('.json'):
                        json.loads(archive.read(name))
                manifest = json.loads(archive.read('manifest.json'))
                ids.extend([manifest['header']['uuid'], manifest['modules'][0]['uuid']])
                self.assertIn('pbr', manifest['capabilities'])
                self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
                lighting = json.loads(archive.read('lighting/mobile_lighting.json'))['minecraft:lighting_settings']['description']['identifier']
                water = json.loads(archive.read('water/mobile_water.json'))['minecraft:water_settings']
                self.assertEqual(water['description']['identifier'], 'realistic_water:water')
                self.assertTrue(1 <= water['waves']['octaves'] <= 4)
                self.assertGreater(water['waves']['depth'], 0)
                if state == 'calm': self.assertLess(water['waves']['depth'], .2)
                else: self.assertGreater(water['waves']['depth'], .2)
                for biome in ('plains', 'forest', 'birch_forest', 'meadow'):
                    components = json.loads(archive.read(f'biomes/{biome}.client_biome.json'))['minecraft:client_biome']['components']
                    self.assertEqual(components['minecraft:water_identifier']['water_identifier'], water['description']['identifier'])
                    self.assertEqual(components['minecraft:lighting_identifier']['lighting_identifier'], lighting)
                    self.assertIn('minecraft:ambient_sounds', components)
                for kind, size in [('still', 128), ('flow', 256)]:
                    base = f'water_{kind}_grey'
                    prefix = 'textures/blocks/'
                    descriptor = json.loads(archive.read(prefix + base + '.texture_set.json'))['minecraft:texture_set']
                    self.assertEqual(descriptor['color'], base)
                    self.assertEqual(descriptor['normal'], f'realistic_{state}_{kind}_normal')
                    self.assertEqual(descriptor['metalness_emissive_roughness_subsurface'], f'realistic_{state}_{kind}_mers')
                    for layer in ('color', 'normal', 'metalness_emissive_roughness_subsurface'):
                        with Image.open(io.BytesIO(archive.read(prefix + descriptor[layer] + '.png'))) as im:
                            self.assertEqual((im.mode, im.size), ('RGBA', (size, size * 16)))
                            frame = im.crop((0, 0, size, size))
                            if layer == 'normal':
                                means = ImageStat.Stat(frame).mean
                                self.assertTrue(124 <= means[0] <= 131)
                                self.assertTrue(124 <= means[1] <= 131)
                                self.assertGreater(means[2], 235)
                            if layer != 'metalness_emissive_roughness_subsurface':
                                next_frame = im.crop((0, size, size, 2 * size))
                                shifted = ImageChops.offset(frame, size // 16, round(size * .025 * math.sin(2 * math.pi / 16)))
                                self.assertEqual(next_frame.tobytes(), shifted.tobytes())
                            if kind == 'still' and layer == 'color': first_frames[state] = frame.tobytes()
        self.assertNotEqual(first_frames['calm'], first_frames['rough'])
        self.assertEqual(len(set(ids)), len(ids))
        for identifier in ids: UUID(identifier)


if __name__ == '__main__':
    unittest.main()
