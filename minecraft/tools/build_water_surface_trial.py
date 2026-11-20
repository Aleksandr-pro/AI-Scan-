#!/usr/bin/env python3
"""Build an A/B water-surface trial for normal Bedrock graphics.

Run from repository root: python3 minecraft/tools/build_water_surface_trial.py
Requires Pillow. Uses the existing photo preparation and animation unchanged,
then moderately increases photograph contrast. No depth sensing is provided.
"""
import json
import zipfile

from PIL import ImageEnhance
from build_water_fancy_experiment import (
    ROOT, SOURCE, prepare_tile, match_edges, make_sheets,
)

DEST = ROOT / 'realistic-water-surface-trial'
TARGET = ROOT / 'realistic-water-surface-trial.mcpack'
HEADER_UUID = '5786eb53-63a8-4358-b643-b363a287f572'
MODULE_UUID = '38666af0-69d1-4648-afb1-c7f57d8b2a61'
CONTRAST = 1.55


def trial_tile(source=SOURCE):
    return match_edges(ImageEnhance.Contrast(prepare_tile(source)).enhance(CONTRAST))


def main():
    textures = DEST / 'textures/blocks'
    textures.mkdir(parents=True, exist_ok=True)
    still, flow = make_sheets(trial_tile())
    still.save(textures / 'water_still_grey.png', optimize=True)
    flow.save(textures / 'water_flow_grey.png', optimize=True)
    manifest = {
        'format_version': 2,
        'header': {
            'name': 'Вода — выразительная поверхность (тест)',
            'description': 'Экспериментальная фотоанимация без VV, без расчёта глубины',
            'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 26, 30],
        },
        'modules': [{'type': 'resources', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = ('manifest.json', 'textures/blocks/water_still_grey.png', 'textures/blocks/water_flow_grey.png')
    found = {p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
    if found != set(files):
        raise ValueError(f'Unexpected files in {DEST}: {found - set(files)}')
    with zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            archive.write(DEST / name, name)
    print(f'Built {TARGET}')


if __name__ == '__main__':
    main()
