#!/usr/bin/env python3
"""Validate particle effect with pinned Mojang Bedrock samples JSON schema.

This validates data shape, not MoLang behaviour, runtime or game rendering.
Requires jsonschema 4.x.
"""
import hashlib
import json
from pathlib import Path
import unittest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[2] / 'minecraft/snow-footprints'
SCHEMA = ROOT / 'reference/mojang-particle-schema.json'
PARTICLE = ROOT / 'resources/particles/footprint.json'

class SchemaTest(unittest.TestCase):
    def test_particle_effect_schema(self):
        data=SCHEMA.read_bytes()
        # Mojang bedrock-samples tag v1.26.30.5, commit 921fafb05c93abeae56c2f2868cd8f942bdbcc0f,
        # metadata/json_schemas/client/particles/1.21.10/Particle Effect Data.json
        self.assertEqual(hashlib.sha256(data).hexdigest(),'825bb454a5ebb2249114dc84b07be219bbc08ee200355d28b16964e723af9203')
        schema=json.loads(data)
        Draft7Validator.check_schema(schema)
        data=json.loads(PARTICLE.read_text(encoding='utf-8'))
        self.assertEqual(data['format_version'],'1.10.0')
        failures=list(Draft7Validator(schema).iter_errors(data['particle_effect']))
        self.assertEqual([f'{list(e.absolute_path)}: {e.message}' for e in failures],[])

if __name__=='__main__':unittest.main()
