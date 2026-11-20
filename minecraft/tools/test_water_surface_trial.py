#!/usr/bin/env python3
"""Verify separate photo surface trial; no test here executes Minecraft."""
import io
import json
import unittest
import zipfile
from uuid import UUID

from PIL import Image, ImageChops, ImageStat
from build_water_fancy_experiment import (
    DEST as BASE, SIZE, FRAMES, STILL_ALPHA, FLOW_ALPHA, SOURCE, wave_frame,
)
from build_water_surface_trial import DEST, TARGET, HEADER_UUID, MODULE_UUID, trial_tile


def diff(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


class SurfaceTrialTests(unittest.TestCase):
    def test_pack_and_photo_animation(self):
        expected_files = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'}
        with zipfile.ZipFile(TARGET) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), expected_files)
            for name in expected_files:
                self.assertEqual(archive.read(name), (DEST / name).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            base_manifest = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))
            for identifier in (HEADER_UUID, MODULE_UUID):
                UUID(identifier)
                self.assertNotIn(identifier, (base_manifest['header']['uuid'], base_manifest['modules'][0]['uuid']))
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            self.assertEqual(manifest['header']['uuid'], HEADER_UUID)
            self.assertEqual(manifest['modules'][0]['uuid'], MODULE_UUID)
            self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
            self.assertNotIn('pbr', manifest.get('capabilities', []))
            tile = trial_tile(SOURCE)
            self.assertEqual(tile.size, (256, 256))
            self.assertEqual(wave_frame(tile, 0).tobytes(), wave_frame(tile, FRAMES).tobytes())
            with Image.open(BASE / 'textures/blocks/water_still_grey.png') as base, \
                 Image.open(io.BytesIO(archive.read('textures/blocks/water_still_grey.png'))) as still, \
                 Image.open(io.BytesIO(archive.read('textures/blocks/water_flow_grey.png'))) as flow:
                self.assertEqual((still.mode, still.size), ('RGBA', (SIZE, SIZE * FRAMES)))
                self.assertEqual((flow.mode, flow.size), ('RGBA', (2*SIZE, 2*SIZE*FRAMES)))
                old = base.crop((0, 0, SIZE, SIZE)).getchannel('R')
                new = still.crop((0, 0, SIZE, SIZE)).getchannel('R')
                self.assertGreater(ImageStat.Stat(new).stddev[0], ImageStat.Stat(old).stddev[0] * 1.35)
                for i in range(FRAMES):
                    frame = wave_frame(tile, i)
                    self.assertLess(diff(frame.crop((0, 0, 1, SIZE)), frame.crop((SIZE-1, 0, SIZE, SIZE))), 1)
                    self.assertLess(diff(frame.crop((0, 0, SIZE, 1)), frame.crop((0, SIZE-1, SIZE, SIZE))), 1)
                    rgba = frame.convert('RGBA')
                    rgba.putalpha(STILL_ALPHA)
                    self.assertEqual(still.crop((0, i*SIZE, SIZE, (i+1)*SIZE)).tobytes(), rgba.tobytes())
                    rgba.putalpha(FLOW_ALPHA)
                    for x in (0, SIZE):
                        for y in (0, SIZE):
                            self.assertEqual(flow.crop((x, i*2*SIZE+y, x+SIZE, i*2*SIZE+y+SIZE)).tobytes(), rgba.tobytes())


if __name__ == '__main__':
    unittest.main()
