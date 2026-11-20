#!/usr/bin/env python3
"""Validate source, pack contents and intended biome overrides, not rendering."""
import copy
import hashlib
import json
import unittest
import zipfile
from uuid import UUID
from build_water_neutral_biomes import (
    BASE_BIOMES, COLOR_DEST, DEST, TARGET, HEADER_UUID, MODULE_UUID, SURFACE_OPACITY,
)


class NeutralWaterBiomeTests(unittest.TestCase):
    def test_pack(self):
        sources = sorted(BASE_BIOMES.glob('*.client_biome.json'))
        self.assertEqual(len(sources), 88)
        sha = hashlib.sha256()
        for f in sources:
            sha.update(f.name.encode() + b'\0' + f.read_bytes())
        self.assertEqual(sha.hexdigest(), '927a0e6757cd5a80487d93251a26cbc9c337bd43dd9dbaf7d66bae958eeea73e')
        paths = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'}
        paths.update('biomes/' + s.name for s in sources)
        seen_ids = set()
        with zipfile.ZipFile(TARGET) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), paths)
            for path in paths:
                self.assertEqual(archive.read(path), (DEST / path).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['header']['uuid'], HEADER_UUID)
            self.assertEqual(manifest['modules'][0]['uuid'], MODULE_UUID)
            UUID(HEADER_UUID); UUID(MODULE_UUID)
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            previous = json.loads((COLOR_DEST / 'manifest.json').read_text(encoding='utf-8'))
            self.assertTrue({HEADER_UUID, MODULE_UUID}.isdisjoint({previous['header']['uuid'], previous['modules'][0]['uuid']}))
            self.assertNotIn('pbr', manifest.get('capabilities', []))
            self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
            self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
            for name in ('water_still_grey.png', 'water_flow_grey.png'):
                self.assertEqual(archive.read('textures/blocks/' + name),
                                 (COLOR_DEST / 'textures/blocks' / name).read_bytes())
            for source in sources:
                vanilla = json.loads(source.read_text(encoding='utf-8'))
                expected = copy.deepcopy(vanilla)
                biome = expected['minecraft:client_biome']
                identifier = biome['description']['identifier']
                self.assertTrue(identifier.startswith('minecraft:'))
                self.assertEqual(source.name, identifier.split(':')[1] + '.client_biome.json')
                self.assertNotIn(identifier, seen_ids)
                seen_ids.add(identifier)
                appearance = biome['components']['minecraft:water_appearance']
                appearance['surface_color'] = '#FFFFFF'
                appearance['surface_opacity'] = SURFACE_OPACITY
                self.assertEqual(json.loads(archive.read('biomes/' + source.name)), expected)
        self.assertTrue({'minecraft:ocean', 'minecraft:deep_ocean', 'minecraft:river', 'minecraft:swampland', 'minecraft:plains', 'minecraft:forest'} <= seen_ids)
        self.assertEqual(SURFACE_OPACITY, .98)


if __name__ == '__main__':
    unittest.main()
