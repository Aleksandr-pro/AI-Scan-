#!/usr/bin/env python3
"""Validate image data and packaging, not Minecraft/device rendering."""
import hashlib
import io
import json
import unittest
import zipfile
from uuid import UUID
from PIL import Image, ImageChops, ImageOps, ImageStat
from build_water_fancy_experiment import SIZE, FRAMES, OVERLAP
from build_water_ocean_trial import DEST as PREVIOUS, STILL_ALPHA as OLD_STILL, FLOW_ALPHA as OLD_FLOW
from build_water_ocean_color_trial import (
    SOURCE, DEST, TARGET, HEADER_UUID, MODULE_UUID, STILL_ALPHA, FLOW_ALPHA,
    color_tile, wave_frame,
)


def diff(a, b):
    means = ImageStat.Stat(ImageChops.difference(a, b)).mean
    return sum(means) / len(means)


class OceanColorTrialTests(unittest.TestCase):
    def test_color_source_animation_and_pack(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'db5ecedfa52883eb1f05d3df75b52f52b4ed0ad26060b5f9c7c8a7fab4bec020')
        with Image.open(SOURCE) as image:
            scaled = ImageOps.fit(ImageOps.exif_transpose(image).convert('RGB'),
                                  (SIZE + 2*OVERLAP, SIZE + 2*OVERLAP), Image.Resampling.LANCZOS)
            original = scaled.crop((OVERLAP, OVERLAP, OVERLAP + SIZE, OVERLAP + SIZE))
        tile = color_tile()
        self.assertEqual(tile.mode, 'RGB')
        interior = (OVERLAP, OVERLAP, SIZE-OVERLAP, SIZE-OVERLAP)
        self.assertEqual(tile.crop(interior).tobytes(), original.crop(interior).tobytes())
        rgb_means = ImageStat.Stat(tile).mean
        self.assertLess(rgb_means[0], rgb_means[1])
        self.assertLess(rgb_means[1], rgb_means[2])
        self.assertLess(sum(rgb_means)/3, 100)
        self.assertGreater(STILL_ALPHA, OLD_STILL)
        self.assertGreater(FLOW_ALPHA, OLD_FLOW)
        self.assertEqual((STILL_ALPHA, FLOW_ALPHA), (246, 250))
        frames = [wave_frame(tile, i) for i in range(FRAMES)]
        self.assertEqual(frames[0].tobytes(), wave_frame(tile, FRAMES).tobytes())
        steps = [diff(frames[i], frames[(i+1)%FRAMES]) for i in range(FRAMES)]
        self.assertGreater(min(steps), 1)
        self.assertLess(max(steps), 14)
        self.assertLess(steps[-1], 1.3*max(steps[:-1]))
        for frame in frames:
            self.assertLess(diff(frame.crop((0, 0, 1, SIZE)), frame.crop((SIZE-1, 0, SIZE, SIZE))), 1)
            self.assertLess(diff(frame.crop((0, 0, SIZE, 1)), frame.crop((0, SIZE-1, SIZE, SIZE))), 1)
        self.check_archive(frames)

    def check_archive(self, frames):
        files = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'}
        with zipfile.ZipFile(TARGET) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), files)
            for name in files:
                self.assertEqual(archive.read(name), (DEST / name).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            previous = json.loads((PREVIOUS / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['header']['uuid'], HEADER_UUID)
            self.assertEqual(manifest['modules'][0]['uuid'], MODULE_UUID)
            UUID(HEADER_UUID); UUID(MODULE_UUID)
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            self.assertTrue({HEADER_UUID, MODULE_UUID}.isdisjoint({previous['header']['uuid'], previous['modules'][0]['uuid']}))
            self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
            self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
            self.assertNotIn('pbr', manifest.get('capabilities', []))
            with Image.open(io.BytesIO(archive.read('textures/blocks/water_still_grey.png'))) as still, \
                 Image.open(io.BytesIO(archive.read('textures/blocks/water_flow_grey.png'))) as flow:
                self.assertEqual((still.mode, still.size), ('RGBA', (SIZE, SIZE*FRAMES)))
                self.assertEqual((flow.mode, flow.size), ('RGBA', (2*SIZE, 2*SIZE*FRAMES)))
                for i, frame in enumerate(frames):
                    expected = frame.convert('RGBA')
                    expected.putalpha(STILL_ALPHA)
                    actual = still.crop((0, i*SIZE, SIZE, (i+1)*SIZE))
                    self.assertEqual(actual.tobytes(), expected.tobytes())
                    self.assertEqual(actual.getchannel('A').getextrema(), (STILL_ALPHA, STILL_ALPHA))
                    self.assertNotEqual(actual.getchannel('R').tobytes(), actual.getchannel('B').tobytes())
                    expected.putalpha(FLOW_ALPHA)
                    for x in (0, SIZE):
                        for y in (0, SIZE):
                            self.assertEqual(flow.crop((x, i*2*SIZE+y, x+SIZE, i*2*SIZE+y+SIZE)).tobytes(), expected.tobytes())


if __name__ == '__main__':
    unittest.main()
