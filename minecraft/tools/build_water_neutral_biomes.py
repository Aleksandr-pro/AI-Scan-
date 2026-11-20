#!/usr/bin/env python3
"""Build an independent RGB water trial with neutral vanilla biome water tints.

Run from repo root. Requires the checked-in 1.26.30.5 Mojang sample client
biomes and previously built ocean-color-trial textures. This is not a shader.
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path('minecraft')
COLOR_DEST = ROOT / 'realistic-water-ocean-color-trial'
BASE_BIOMES = ROOT / 'vanilla-client-biomes-1.26.30.5'
DEST = ROOT / 'realistic-water-neutral-biomes'
TARGET = ROOT / 'realistic-water-neutral-biomes.mcpack'
HEADER_UUID = '06e36a72-5606-42cc-8afa-1b4ce067c882'
MODULE_UUID = '027ba6b8-260b-417c-b942-ccf93eab69bb'
SURFACE_OPACITY = 0.98


def main():
    originals = sorted(BASE_BIOMES.glob('*.client_biome.json'))
    if len(originals) != 88:
        raise ValueError(f'Expected 88 pinned Mojang biome files, found {len(originals)}')
    biomes = DEST / 'biomes'
    textures = DEST / 'textures/blocks'
    biomes.mkdir(parents=True, exist_ok=True)
    textures.mkdir(parents=True, exist_ok=True)
    names = []
    for source in originals:
        biome = json.loads(source.read_text(encoding='utf-8'))
        appearance = biome['minecraft:client_biome']['components']['minecraft:water_appearance']
        appearance['surface_color'] = '#FFFFFF'
        appearance['surface_opacity'] = SURFACE_OPACITY
        dest = biomes / source.name
        dest.write_text(json.dumps(biome, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        names.append('biomes/' + source.name)
    for name in ('water_still_grey.png', 'water_flow_grey.png'):
        shutil.copyfile(COLOR_DEST / 'textures/blocks' / name, textures / name)
        names.append('textures/blocks/' + name)
    manifest = {
        'format_version': 2,
        'header': {'name': 'Вода — океан без цвета биомов (тест)',
                   'description': 'Цветное фото воды, нейтральный цвет в стандартных биомах',
                   'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30]},
        'modules': [{'type': 'resources', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    names.append('manifest.json')
    actual = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    if actual != set(names):
        raise ValueError(f'Unexpected files: {actual ^ set(names)}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            archive.write(DEST / name, name)
    print(f'Built {TARGET}: {len(originals)} vanilla biomes')


if __name__ == '__main__':
    main()
