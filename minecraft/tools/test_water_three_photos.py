#!/usr/bin/env python3
"""Checks assets and loops, not actual Bedrock rendering or projected light."""
import hashlib
import io
import json
import unittest
import zipfile
from uuid import UUID
from PIL import Image, ImageChops, ImageStat
from build_water_fancy_experiment import SIZE, FRAMES
from build_water_neutral_biomes import BASE_BIOMES, DEST as PREV_DEST
from build_water_ocean_color_trial import color_tile, wave_frame
from build_water_three_photos import (
    SOURCE_SURFACE, SOURCE_DEEP, SOURCE_CAUSTICS, DEST, TARGET, CAUSTICS_STRIP,
    CAUSTICS_GIF, HEADER_UUID, MODULE_UUID, STILL_ALPHA, FLOW_ALPHA,
    SURFACE_OPACITY, DEEP_BLEND, surface_tile,
)


def diff(a, b):
    means = ImageStat.Stat(ImageChops.difference(a, b)).mean
    return sum(means) / len(means)


class ThreePhotosWaterTests(unittest.TestCase):
    def test_assets_and_pack(self):
        for source, digest in (
            (SOURCE_CAUSTICS, 'fb7234487e5ea25d47210cd8ce14715aff948c8712d8dffb10ddf1af3fbac96e'),
            (SOURCE_DEEP, '5e5c15cba239b439da475847ad96298b568746ea9efaadbed910b18cba1e6317'),
            (SOURCE_SURFACE, '0daf03bf67f5e3f6fa0f650ab771c14d8ae7a0e1666517f9b25c81d3fb09d39a'),
        ):
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
            with Image.open(source) as img:
                self.assertEqual((img.mode, img.size), ('RGB', (1254, 1254)))
        tile = surface_tile()
        surface, deep = color_tile(SOURCE_SURFACE), color_tile(SOURCE_DEEP)
        self.assertEqual(DEEP_BLEND, .25)
        self.assertEqual(tile.crop((40, 40, 216, 216)).tobytes(), Image.blend(surface, deep, DEEP_BLEND).crop((40, 40, 216, 216)).tobytes())
        self.assertGreater(diff(tile, surface), .1)
        self.assertGreater(diff(tile, deep), .1)
        self.assertLess(SURFACE_OPACITY, .98)
        self.assertEqual((SURFACE_OPACITY, STILL_ALPHA, FLOW_ALPHA), (.92, 230, 240))
        frames = self.check_loop(tile)
        self.check_caustics_preview()
        self.check_archive(frames)

    def check_loop(self, tile):
        frames = [wave_frame(tile, i) for i in range(FRAMES)]
        self.assertEqual(frames[0].tobytes(), wave_frame(tile, FRAMES).tobytes())
        steps = [diff(frames[i], frames[(i+1)%FRAMES]) for i in range(FRAMES)]
        self.assertGreater(min(steps), 1)
        self.assertLess(max(steps), 9)
        self.assertLess(steps[-1], max(steps[:-1]) * 1.3)
        for f in frames:
            self.assertLess(diff(f.crop((0, 0, 1, SIZE)), f.crop((SIZE-1, 0, SIZE, SIZE))), 1)
            self.assertLess(diff(f.crop((0, 0, SIZE, 1)), f.crop((0, SIZE-1, SIZE, SIZE))), 1)
        return frames

    def check_caustics_preview(self):
        frames = self.check_loop(color_tile(SOURCE_CAUSTICS))
        with Image.open(CAUSTICS_STRIP) as strip:
            self.assertEqual((strip.mode, strip.size), ('RGB', (SIZE, SIZE*FRAMES)))
            for i, frame in enumerate(frames):
                self.assertEqual(frame.tobytes(), strip.crop((0, i*SIZE, SIZE, (i+1)*SIZE)).tobytes())
        with Image.open(CAUSTICS_GIF) as gif:
            self.assertEqual(gif.size, (SIZE, SIZE))
            self.assertEqual(gif.n_frames, FRAMES)
            self.assertEqual(gif.info['loop'], 0)
            for i, frame in enumerate(frames):
                gif.seek(i)
                self.assertEqual(gif.info['duration'], 100)
                self.assertLess(diff(gif.convert('RGB'), frame), 2)

    def check_archive(self, frames):
        sources = sorted(BASE_BIOMES.glob('*.client_biome.json'))
        self.assertEqual(len(sources), 88)
        names = {'manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png'} | {'biomes/' + s.name for s in sources}
        with zipfile.ZipFile(TARGET) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), names)
            for path in names:
                self.assertEqual(archive.read(path), (DEST / path).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            previous = json.loads((PREV_DEST / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual((manifest['header']['uuid'], manifest['modules'][0]['uuid']), (HEADER_UUID, MODULE_UUID))
            UUID(HEADER_UUID); UUID(MODULE_UUID)
            self.assertNotEqual(HEADER_UUID, MODULE_UUID)
            self.assertTrue({HEADER_UUID, MODULE_UUID}.isdisjoint({previous['header']['uuid'], previous['modules'][0]['uuid']}))
            self.assertNotIn('pbr', manifest.get('capabilities', []))
            self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
            for source in sources:
                expected = json.loads(source.read_text(encoding='utf-8'))
                appearance = expected['minecraft:client_biome']['components']['minecraft:water_appearance']
                appearance['surface_color'], appearance['surface_opacity'] = '#FFFFFF', SURFACE_OPACITY
                self.assertEqual(json.loads(archive.read('biomes/' + source.name)), expected)
            with Image.open(io.BytesIO(archive.read('textures/blocks/water_still_grey.png'))) as still, \
                 Image.open(io.BytesIO(archive.read('textures/blocks/water_flow_grey.png'))) as flow:
                self.assertEqual((still.mode, still.size), ('RGBA', (SIZE, SIZE*FRAMES)))
                self.assertEqual((flow.mode, flow.size), ('RGBA', (2*SIZE, 2*SIZE*FRAMES)))
                for i, f in enumerate(frames):
                    expected = f.convert('RGBA'); expected.putalpha(STILL_ALPHA)
                    actual = still.crop((0, i*SIZE, SIZE, (i+1)*SIZE))
                    self.assertEqual(actual.tobytes(), expected.tobytes())
                    self.assertNotEqual(actual.getchannel('R').tobytes(), actual.getchannel('B').tobytes())
                    expected.putalpha(FLOW_ALPHA)
                    for x in (0, SIZE):
                        for y in (0, SIZE):
                            self.assertEqual(flow.crop((x, i*2*SIZE+y, x+SIZE, i*2*SIZE+y+SIZE)).tobytes(), expected.tobytes())


if __name__ == '__main__':
    unittest.main()
