#!/usr/bin/env python3
"""Validate the packaged behavior pack without pretending to run Minecraft."""
import json
import unittest
import zipfile
from pathlib import Path
from uuid import UUID

ROOT = Path('minecraft')
PACK = ROOT / 'realistic-rain-water'


class RainWaterArchiveTests(unittest.TestCase):
    def test_pack(self):
        with zipfile.ZipFile(ROOT / 'realistic-rain-water.mcpack') as archive:
            self.assertIsNone(archive.testzip())
            expected = {p.relative_to(PACK).as_posix() for p in PACK.rglob('*') if p.is_file()}
            self.assertEqual(set(archive.namelist()), expected)
            for name in expected:
                self.assertEqual(archive.read(name), (PACK / name).read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['header']['min_engine_version'], [1, 26, 30])
            self.assertEqual(manifest['dependencies'], [{'module_name': '@minecraft/server', 'version': '2.8.0'}])
            self.assertEqual({m['type'] for m in manifest['modules']}, {'data', 'script'})
            module = next(m for m in manifest['modules'] if m['type'] == 'script')
            self.assertEqual((module['type'], module['language'], module['entry']), ('script', 'javascript', 'scripts/main.js'))
            ids = [manifest['header']['uuid']] + [m['uuid'] for m in manifest['modules']]
            for item in ids:
                UUID(item)
            self.assertEqual(len(set(ids)), len(ids))
            self.assertIn(module['entry'], expected)
            self.assertIn('scripts/puddles.js', expected)


if __name__ == '__main__':
    unittest.main()
