#!/usr/bin/env python3
"""Validate pack structure, provenance, sample characteristics and archive parity."""
import hashlib
import json
from pathlib import Path
import unittest
import uuid
import zipfile

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'realistic-sounds'
ARCHIVE = ROOT / 'realistic-sounds.mcpack'
VANILLA = json.loads((ROOT / 'sound-reference/vanilla-sound-definitions.json').read_text())['sound_definitions']
CUSTOM = 'sounds/realistic_audio/'


class SoundPackTests(unittest.TestCase):
    def test_manifest(self):
        manifest = json.loads((PACK / 'manifest.json').read_text())
        self.assertEqual(manifest['format_version'], 2)
        self.assertEqual(manifest['modules'][0]['type'], 'resources')
        a, b = manifest['header']['uuid'], manifest['modules'][0]['uuid']
        uuid.UUID(a); uuid.UUID(b)
        self.assertNotEqual(a, b)
        other = json.loads((ROOT / 'realistic-dirt/manifest.json').read_text())
        self.assertNotIn(a, [other['header']['uuid'], other['modules'][0]['uuid']])
        self.assertGreaterEqual(manifest['header']['min_engine_version'], [1, 21, 0])

    def test_catalog_and_audio(self):
        doc = json.loads((PACK / 'sounds/sound_definitions.json').read_text())
        self.assertEqual(doc['format_version'], '1.20.20')
        defs = doc['sound_definitions']
        self.assertEqual(set(defs), set(VANILLA))
        referenced = set()
        for key, definition in defs.items():
            for prop, value in VANILLA[key].items():
                if prop != 'sounds':
                    self.assertEqual(definition[prop], value)
            for entry in definition['sounds']:
                name = entry if isinstance(entry, str) else entry['name']
                if not name.startswith(CUSTOM):
                    self.assertEqual(key, 'ambient.cave')
                    self.assertIn(name, VANILLA[key]['sounds'])
                    continue
                path = PACK / (name + '.ogg')
                self.assertTrue(path.is_file(), name)
                referenced.add(path)
                info = sf.info(path)
                self.assertEqual((info.format, info.subtype, info.channels, info.samplerate),
                                 ('OGG', 'VORBIS', 1, 22050))
                samples, _ = sf.read(path)
                peak = np.max(np.abs(samples))
                rms = np.sqrt(np.mean(samples ** 2))
                self.assertGreater(rms, .005, name)
                self.assertLess(peak, .95, name)
                self.assertLess(abs(samples[0]), .01, name)
                self.assertLess(abs(samples[-1]), .01, name)
                self.assertLess(info.duration, 8, name)
        self.assertEqual(referenced, set(PACK.rglob('*.ogg')))
        self.assertEqual(len(referenced), 57)
        self.assertEqual(len(defs['ambient.cave']['sounds']), 27)
        self.assertTrue(all(s['volume'] == .02 for s in defs['ambient.weather.rain']['sounds']))

    def test_sources(self):
        sources = json.loads((ROOT / 'sound-reference/source-manifest.json').read_text())['files']
        self.assertEqual(set(sources), {p.name for p in (ROOT / 'sound-reference/source').glob('*.mp3')})
        for name, record in sources.items():
            self.assertEqual(hashlib.sha256((ROOT / 'sound-reference/source' / name).read_bytes()).hexdigest(), record['sha256'])
            self.assertTrue(record['source_ids'])

    def test_archive_is_exact(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            self.assertIsNone(archive.testzip())
            files = {p.relative_to(PACK).as_posix(): p for p in PACK.rglob('*') if p.is_file()}
            self.assertEqual(set(archive.namelist()), set(files))
            for name, path in files.items():
                self.assertEqual(archive.read(name), path.read_bytes(), name)
            self.assertLess(ARCHIVE.stat().st_size, 3 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
