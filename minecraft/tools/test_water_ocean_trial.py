#!/usr/bin/env python3
"""Check the ocean trial's assets, not its rendering on a device."""
import hashlib
import io
import json
import math
import unittest
import zipfile
from uuid import UUID

from PIL import Image, ImageChops, ImageOps, ImageStat
from build_water_fancy_experiment import (
    SIZE, FRAMES, OVERLAP, STILL_ALPHA, FLOW_ALPHA, wave_frame as old_wave,
)
from build_water_ocean_trial import (
    SOURCE, DEST, TARGET, HEADER_UUID, MODULE_UUID, ocean_tile, wave_frame,
)


def diff(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


class OceanTrialTests(unittest.TestCase):
    def test_photo_and_animation(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'db5ecedfa52883eb1f05d3df75b52f52b4ed0ad26060b5f9c7c8a7fab4bec020')
        with Image.open(SOURCE) as source:
            self.assertEqual(source.size, (1254, 1254))
            scaled = ImageOps.fit(ImageOps.exif_transpose(source).convert('L'),
                                  (SIZE + 2*OVERLAP, SIZE + 2*OVERLAP), Image.Resampling.LANCZOS)
            original = scaled.crop((OVERLAP, OVERLAP, OVERLAP+SIZE, OVERLAP+SIZE))
        tile = ocean_tile()
        rect = (40, 40, SIZE-40, SIZE-40)
        a, b = original.crop(rect).tobytes(), tile.crop(rect).tobytes()
        ma, mb = sum(a)/len(a), sum(b)/len(b)
        cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
        denominator = math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
        self.assertGreater(cov / denominator, .90)
        frames = [wave_frame(tile, i) for i in range(FRAMES)]
        old_frames = [old_wave(tile, i) for i in range(FRAMES)]
        steps = [diff(frames[i], frames[(i+1) % FRAMES]) for i in range(FRAMES)]
        old_steps = [diff(old_frames[i], old_frames[(i+1) % FRAMES]) for i in range(FRAMES)]
        self.assertGreater(sum(steps), 1.4 * sum(old_steps))
        self.assertLess(max(steps), 8)
        self.assertLess(steps[-1], 1.3 * max(steps[:-1]))
        self.assertEqual(frames[0].tobytes(), wave_frame(tile, FRAMES).tobytes())
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
            self.assertEqual(manifest['header']['uuid'], HEADER_UUID)
            self.assertEqual(manifest['modules'][0]['uuid'], MODULE_UUID)
            UUID(HEADER_UUID); UUID(MODULE_UUID)
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            for other in ('realistic-water-fancy-experiment', 'realistic-water-surface-trial'):
                previous = json.loads((DEST.parent / other / 'manifest.json').read_text(encoding='utf-8'))
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
                    r, g, b, a = actual.split()
                    self.assertEqual(r.tobytes(), g.tobytes())
                    self.assertEqual(r.tobytes(), b.tobytes())
                    self.assertEqual(a.getextrema(), (STILL_ALPHA, STILL_ALPHA))
                    expected.putalpha(FLOW_ALPHA)
                    for x in (0, SIZE):
                        for y in (0, SIZE):
                            self.assertEqual(flow.crop((x, i*2*SIZE+y, x+SIZE, i*2*SIZE+y+SIZE)).tobytes(), expected.tobytes())


if __name__ == '__main__':
    unittest.main()
