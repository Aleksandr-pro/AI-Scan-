#!/usr/bin/env python3
"""Validate normal-renderer water packages, not an in-game render test."""
import io
import json
import unittest
import zipfile
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageChops, ImageStat
from build_classic_water import BASE, FRAMES, PROFILES, ROOT, SIZE, frame_for, prepare_tile


def difference(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean[:3]) / 3


class ClassicWaterTests(unittest.TestCase):
    def test_archives_and_animation(self):
        all_ids = set()
        first_frames = []
        for profile, info in PROFILES.items():
            folder = BASE / profile
            with zipfile.ZipFile(ROOT / f'realistic-water-classic-{profile}.mcpack') as archive:
                self.assertIsNone(archive.testzip())
                names = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'}
                self.assertEqual(set(archive.namelist()), names)
                for name in names:
                    self.assertEqual(archive.read(name), (folder / name).read_bytes())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertNotIn('pbr', manifest.get('capabilities', []))
                self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
                self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
                for identifier in (manifest['header']['uuid'], manifest['modules'][0]['uuid']):
                    UUID(identifier)
                    self.assertNotIn(identifier, all_ids)
                    all_ids.add(identifier)
                tile = prepare_tile(ROOT / 'water-reference' / info['source'])
                x_seam = difference(tile.crop((0, 0, 1, SIZE)), tile.crop((SIZE-1, 0, SIZE, SIZE)))
                x_detail = difference(tile.crop((0, 0, SIZE-1, SIZE)), tile.crop((1, 0, SIZE, SIZE)))
                y_seam = difference(tile.crop((0, 0, SIZE, 1)), tile.crop((0, SIZE-1, SIZE, SIZE)))
                y_detail = difference(tile.crop((0, 0, SIZE, SIZE-1)), tile.crop((0, 1, SIZE, SIZE)))
                self.assertLess(x_seam, x_detail * 1.3)
                self.assertLess(y_seam, y_detail * 1.3)
                with Image.open(io.BytesIO(archive.read('textures/blocks/water_still_grey.png'))) as still, \
                     Image.open(io.BytesIO(archive.read('textures/blocks/water_flow_grey.png'))) as flow:
                    self.assertEqual((still.mode, still.size), ('RGBA', (SIZE, SIZE * FRAMES)))
                    self.assertEqual((flow.mode, flow.size), ('RGBA', (2 * SIZE, 2 * SIZE * FRAMES)))
                    first_frames.append(still.crop((0, 0, SIZE, SIZE)).tobytes())
                    self.assertNotEqual(first_frames[-1], still.crop((0, SIZE, SIZE, SIZE * 2)).tobytes())
                    for i in range(FRAMES):
                        expected = frame_for(tile, i).convert('RGBA')
                        expected.putalpha(240)
                        self.assertEqual(still.crop((0, i * SIZE, SIZE, (i+1) * SIZE)).tobytes(), expected.tobytes())
                        expected.putalpha(255)
                        for x in (0, SIZE):
                            for y in (0, SIZE):
                                self.assertEqual(flow.crop((x, i * 2 * SIZE + y, x + SIZE, i * 2 * SIZE + y + SIZE)).tobytes(), expected.tobytes())
        self.assertNotEqual(*first_frames)
        for state in ('calm', 'rough'):
            old = json.loads((ROOT / 'realistic-water' / state / 'manifest.json').read_text())
            self.assertNotIn(old['header']['uuid'], all_ids)
            self.assertNotIn(old['modules'][0]['uuid'], all_ids)


if __name__ == '__main__':
    unittest.main()
