#!/usr/bin/env python3
"""Check that the distributable preserves source files and texture references."""
import json
import zipfile
from pathlib import Path

root = Path('minecraft/realistic-dirt')
pack = Path('minecraft/realistic-dirt.mcpack')


def texture_paths(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'path' and isinstance(child, str):
                yield child
            else:
                yield from texture_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from texture_paths(child)
    elif isinstance(value, str) and value.startswith('textures/'):
        yield value


with zipfile.ZipFile(pack) as archive:
    assert archive.testzip() is None, 'Corrupt archive'
    names = set(archive.namelist())
    terrain = json.loads(archive.read('textures/terrain_texture.json'))
    paths = set(texture_paths(terrain))
    for texture in paths:
        assert any(texture + ext in names for ext in ('.png', '.tga')), f'Missing {texture}'
    omitted = []
    for file in root.rglob('*'):
        if not file.is_file():
            continue
        name = file.relative_to(root).as_posix()
        if name in names:
            assert archive.read(name) == file.read_bytes(), f'Changed {name}'
            continue
        # Only an identical zero-variant may be absent; its base and source
        # remain, and its old name must not still be referenced by the atlas.
        assert name.endswith('_variant_0.png'), f'Unexpected omitted file: {name}'
        base = name.removesuffix('_variant_0.png') + '.png'
        assert base in names and archive.read(base) == file.read_bytes(), f'Non-identical {name}'
        assert base.removesuffix('.png') in paths, f'Base not referenced: {base}'
        assert name.removesuffix('.png') not in paths, f'Stale atlas reference: {name}'
        omitted.append(name)
    assert len(names) + len(omitted) == sum(1 for p in root.rglob('*') if p.is_file()), 'Unexpected archive entries'
    print(f'Archive valid: {len(names)} files, {len(paths)} atlas paths, {len(omitted)} identical variants reused.')
