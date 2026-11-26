#!/usr/bin/env python3
"""Regression tests for the generated Bedrock ID catalog; no dependencies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'КАТАЛОГ-МАЙНКРАФТ.md'
SRC=ROOT/'minecraft/catalog-source/bedrock-1.26.30.5'
PACK=ROOT/'minecraft/realistic-dirt.mcpack'


def section(text,heading,next_heading):
    return text.split('## '+heading+'\n',1)[1].split('\n## '+next_heading+'\n',1)[0]


def ids(text):
    return re.findall(r'^- (?:✅|🟨|❌|❔) \*\*.*?\*\* — `([^`]+)`',text,re.M)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=DOC.read_text(encoding='utf-8')

    def test_snapshot_and_generator_are_deterministic(self):
        # The user chose not to maintain the saved catalog. It is a historical
        # snapshot, not a live claim about the current resource pack. Exercise
        # the generator twice in a temporary directory without rewriting it.
        before=DOC.read_bytes()
        spec=importlib.util.spec_from_file_location('catalog_determinism',ROOT/'minecraft/tools/build_texture_catalog.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.OUTPUT=Path(tmp)/'catalog.md'
            module.main()
            first=module.OUTPUT.read_bytes()
            module.main()
            self.assertEqual(first,module.OUTPUT.read_bytes())
            self.assertIn(hashlib.sha256(PACK.read_bytes()).hexdigest(),first.decode('utf-8'))
        self.assertEqual(before,DOC.read_bytes(),'Generator test changed the saved snapshot')
        self.assertIn('1.26.32.2',self.text)
        self.assertIn('v1.26.30.5',self.text)

    def test_every_primary_id_once(self):
        block_text=section(self.text,'Растения и растительные блоки','Предметы')
        item_text=section(self.text,'Предметы','Сущности дополнительно')
        entity_text=section(self.text,'Сущности дополнительно','Дополнительные названия вариантов')
        for name,text in [('blocks',block_text),('items',item_text),('entities',entity_text)]:
            source=json.loads((SRC/f'mojang-{name}.json').read_text(encoding='utf-8'))['data_items']
            expected={r['name'].split(':',1)[-1] for r in source}
            actual=ids(text)
            self.assertEqual(len(actual),len(expected),name)
            self.assertEqual(set(actual),expected,name)

    def test_examples_and_status_scope(self):
        block_text=section(self.text,'Растения и растительные блоки','Предметы')
        item_text=section(self.text,'Предметы','Сущности дополнительно')
        for ident in ('oak_planks','andesite','andesite_slab','red_concrete','oak_shelf','flower_pot','poppy'):
            self.assertRegex(block_text,rf'(?m)^- ✅ .* — `{ident}`')
        self.assertRegex(item_text,r'(?m)^- ❌ \*\*Око Эндера\*\* — `ender_eye`')
        self.assertRegex(item_text,r'(?m)^- 🟨 .* — `oak_planks`')
        self.assertRegex(block_text,r'(?m)^- ❌ .* — `water`') # water is a separate pack
        self.assertIn('не проверка в игре',self.text)
        self.assertIn('отдельный значок',item_text)
        self.assertIn('не доказательство полного совпадения',self.text)

    def test_manual_override_is_preserved_by_generation(self):
        spec=importlib.util.spec_from_file_location('catalog_builder',ROOT/'minecraft/tools/build_texture_catalog.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.OVERRIDES=Path(tmp)/'overrides.json'
            module.OUTPUT=Path(tmp)/'catalog.md'
            module.OVERRIDES.write_text(json.dumps({'blocks':{'water':{'status':'done','note':'проверка теста'}}}),encoding='utf-8')
            module.main()
            text=module.OUTPUT.read_text(encoding='utf-8')
            block_text=section(text,'Растения и растительные блоки','Предметы')
            self.assertRegex(block_text,r'(?m)^- ✅ .* — `water` · проверка теста$')
            self.assertEqual(DOC.read_text(encoding='utf-8'),self.text)

    def test_primary_names_and_additional_aliases(self):
        block_text=section(self.text,'Растения и растительные блоки','Предметы')
        extras=section(self.text,'Возможные старые и технические ID','Источники и обновление')
        for ident in ('air','element_118','oak_planks','short_grass'):
            self.assertIn(f'`{ident}`',block_text)
        self.assertIn('`end_gateway`',extras)
        self.assertIn('версия не подтверждена',extras)
        self.assertIn('локализации',self.text)
        self.assertIn('status-overrides.json',self.text)
        self.assertLess(DOC.stat().st_size,512*1024,'Keep the main catalogue reasonably viewable on GitHub')

if __name__=='__main__':unittest.main()
