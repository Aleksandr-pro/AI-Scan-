#!/usr/bin/env python3
"""Resource/animation checks for the experimental water, not an engine test."""
import hashlib
import io
import json
import math
import unittest
import zipfile
from uuid import UUID

from PIL import Image, ImageChops, ImageOps, ImageStat
from build_water_fancy_experiment import (
    DEST, TARGET, SOURCE, SIZE, FRAMES, OVERLAP, STILL_ALPHA, FLOW_ALPHA,
    HEADER_UUID, MODULE_UUID, prepare_tile, wave_frame,
)


def mean_diff(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


class WaterFancyExperimentTests(unittest.TestCase):
    def test_content_and_manifest(self):
        files = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'}
        with zipfile.ZipFile(TARGET) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), files)
            for name in files:
                self.assertEqual(archive.read(name), (DEST / name).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['header']['uuid'], HEADER_UUID)
            self.assertEqual(manifest['modules'][0]['uuid'], MODULE_UUID)
            UUID(HEADER_UUID)
            UUID(MODULE_UUID)
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            self.assertNotIn('pbr', manifest.get('capabilities', []))
            self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
            self.assertEqual(manifest['header']['version'], [1, 1, 0])
            self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
            self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), '471134cf029e244cdc234d9f18df487e69642fc4d8e931bda6dfa5e9bb857832')
            with Image.open(SOURCE) as source:
                self.assertEqual(source.size, (1024, 1024))
                extent = SIZE + 2*OVERLAP
                scaled = ImageOps.fit(ImageOps.exif_transpose(source).convert('L'),
                                      (extent, extent), Image.Resampling.LANCZOS)
                original = scaled.crop((OVERLAP, OVERLAP, OVERLAP+SIZE, OVERLAP+SIZE))
            photo_tile = prepare_tile(SOURCE)
            self.assertEqual(photo_tile.mode, 'L')
            self.assertEqual(photo_tile.size, (256, 256))
            self.assertEqual(FRAMES, 16)
            self.assertLessEqual(2 * SIZE * FRAMES, 8192)
            # Verify preservation of photographic detail away from blended borders.
            rect = (40, 40, SIZE-40, SIZE-40)
            a = original.crop(rect).tobytes()
            b = photo_tile.crop(rect).tobytes()
            ma, mb = sum(a)/len(a), sum(b)/len(b)
            cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
            denom = math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
            self.assertGreater(cov / denom, .95)
            self.assertEqual(wave_frame(photo_tile, 0).tobytes(), wave_frame(photo_tile, FRAMES).tobytes())
            frames = [wave_frame(photo_tile, i) for i in range(FRAMES)]
            steps = [mean_diff(frames[i], frames[(i + 1) % FRAMES]) for i in range(FRAMES)]
            self.assertGreater(min(steps), .1)
            self.assertLess(max(steps), 5)
            self.assertLess(steps[-1], max(steps[:-1]) * 1.3)
            with Image.open(io.BytesIO(archive.read('textures/blocks/water_still_grey.png'))) as still, \
                 Image.open(io.BytesIO(archive.read('textures/blocks/water_flow_grey.png'))) as flow:
                self.assertEqual((still.mode, still.size), ('RGBA', (SIZE, SIZE * FRAMES)))
                self.assertEqual((flow.mode, flow.size), ('RGBA', (2*SIZE, 2*SIZE*FRAMES)))
                for i, frame in enumerate(frames):
                    # Identical boundary pixels prevent an image-level seam;
                    # they cannot prevent repetition or GPU filtering artefacts.
                    self.assertLess(mean_diff(frame.crop((0, 0, 1, SIZE)), frame.crop((SIZE-1, 0, SIZE, SIZE))), 1)
                    self.assertLess(mean_diff(frame.crop((0, 0, SIZE, 1)), frame.crop((0, SIZE-1, SIZE, SIZE))), 1)
                    expected = frame.convert('RGBA')
                    expected.putalpha(STILL_ALPHA)
                    actual = still.crop((0, i*SIZE, SIZE, (i+1)*SIZE))
                    self.assertEqual(actual.tobytes(), expected.tobytes())
                    r, g, b, alpha = actual.split()
                    self.assertEqual(r.tobytes(), g.tobytes())
                    self.assertEqual(r.tobytes(), b.tobytes())
                    self.assertEqual(alpha.getextrema(), (STILL_ALPHA, STILL_ALPHA))
                    # A constant/blank frame would not be a water texture.
                    self.assertGreater(ImageStat.Stat(r).stddev[0], 5)
                    self.assertLess(ImageStat.Stat(r).stddev[0], 25)
                    expected.putalpha(FLOW_ALPHA)
                    for x in (0, SIZE):
                        for y in (0, SIZE):
                            self.assertEqual(flow.crop((x, i*2*SIZE+y, x+SIZE, i*2*SIZE+y+SIZE)).tobytes(), expected.tobytes())


if __name__ == '__main__':
    unittest.main()
