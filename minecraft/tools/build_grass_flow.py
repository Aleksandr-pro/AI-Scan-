#!/usr/bin/env python3
"""Build an isolated, opt-in 32x32 Bedrock density-map experiment.
Uses the four user photographs, Pillow, NumPy, SciPy and Node.js.
No changes to the main resource pack or vanilla blocks.
"""
from pathlib import Path
import io
import itertools
import json
import subprocess
import zipfile
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from prepare_cobblestone import prepare

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'grass-flow-experiment'
RP, BP = ADDON / 'resources', ADDON / 'behavior'
N = 128
SUPER = 2 * N - 1
SRC = ROOT / 'grass-top-reference'
FILES = ['01_sparse.jpg', '02_sparse.jpg', '03_grassy.jpg', '04_dense.jpg']
RHEAD, RMOD = '07e733e9-d5e9-4133-b826-29571da21290', '28e84c39-ae80-4b74-bd48-582c5229a66d'
BHEAD, BMOD, BSCRIPT = '06cce6ab-8293-43d2-af08-b21f4b09e986', 'e19bd031-9f0b-4c89-88f5-d032c6d6644d', '1e97545d-d62c-4149-ba04-591aabf38c3c'
KEYS = ('nw', 'ne', 'sw', 'se', 'detail')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def periodic_source(filename):
    img = prepare(SRC / filename).resize((SUPER, SUPER), Image.Resampling.LANCZOS)
    arr = np.asarray(img, dtype=np.float64).copy()
    # Guarantee exactly equal opposing edge texels, including all four corners.
    vertical = (arr[0] + arr[-1]) * .5
    arr[0] = arr[-1] = vertical
    horizontal = (arr[:, 0] + arr[:, -1]) * .5
    arr[:, 0] = arr[:, -1] = horizontal
    return arr


def get_tiles():
    sources = np.stack([periodic_source(f) for f in FILES])
    rng = np.random.default_rng(202610)
    shape = (SUPER - 1, SUPER - 1)
    large = gaussian_filter(rng.standard_normal(shape), 9, mode='wrap')
    fine = gaussian_filter(rng.standard_normal(shape), 3, mode='wrap')
    def normalize(a):
        return (a - a.mean()) / (a.std() + 1e-9)
    noise = np.clip(normalize(large)*.68 + normalize(fine)*.18, -1.5, 1.5)
    noise = np.pad(noise, ((0, 1), (0, 1)), mode='wrap')
    yy, xx = np.mgrid[0:N, 0:N].astype(float) / (N - 1)
    texture_dir = RP / 'textures/blocks'
    texture_dir.mkdir(parents=True, exist_ok=True)
    for old in texture_dir.glob('grassflow_*.png'):
        old.unlink()
    tiles = {}
    # Four quadrants of a 2x2 photographic supertile. Shared pixels at each
    # boundary keep phases continuous, avoiding one repeated image per block.
    for c in itertools.product(range(3), range(3), range(3), range(3), range(4)):
        nw, ne, sw, se, detail = c
        sx, sy = (detail % 2) * (N-1), (detail // 2) * (N-1)
        local_sources = sources[:, sy:sy+N, sx:sx+N, :]
        local_noise = noise[sy:sy+N, sx:sx+N]
        level = (nw*(1-xx)*(1-yy) + ne*xx*(1-yy) + sw*(1-xx)*yy + se*xx*yy)
        # Irregular transitions in the middle, still exactly matching across edges.
        selection = np.clip(level * 1.5 + local_noise * .48 * np.sin(np.pi * level / 2), 0, 3)
        base = np.floor(selection).astype(np.int32).clip(0, 2)
        frac = selection - base
        t = np.clip((frac - .34) / .32, 0, 1)
        t = t*t*(3-2*t)
        layers = local_sources.transpose(1, 2, 0, 3)
        a = np.take_along_axis(layers, base[..., None, None], axis=2)[:, :, 0, :]
        b = np.take_along_axis(layers, (base+1)[..., None, None], axis=2)[:, :, 0, :]
        rgb = np.rint(a*(1-t[..., None]) + b*t[..., None]).clip(0,255).astype('uint8')
        name = 'grassflow_' + ''.join(map(str, c))
        tile = Image.fromarray(rgb, 'RGB')
        tile.save(texture_dir / f'{name}.png', optimize=True)
        tiles[c] = tile
    dirt = Image.open(ROOT / 'realistic-dirt/textures/blocks/dirt.png').convert('RGB').resize((N, N), Image.Resampling.LANCZOS)
    dirt.save(texture_dir / 'grassflow_dirt.png', optimize=True)
    return tiles


def build_data(tiles):
    version = [1, 0, 0]
    write_json(RP / 'manifest.json', {'format_version': 2,
        'header': {'name': 'Живая почва — ресурсы (эксперимент)', 'description': 'Карта плотности травы: отдельная площадка', 'uuid': RHEAD, 'version': version, 'min_engine_version': [1,26,30]},
        'modules': [{'type': 'resources', 'uuid': RMOD, 'version': version}]})
    write_json(BP / 'manifest.json', {'format_version': 2,
        'header': {'name': 'Живая почва — эксперимент', 'description': 'Создает тестовую площадку только по команде в пустом пространстве', 'uuid': BHEAD, 'version': version, 'min_engine_version': [1,26,30]},
        'modules': [{'type': 'data', 'uuid': BMOD, 'version': version},
                    {'type': 'script', 'language': 'javascript', 'entry': 'scripts/main.js', 'uuid': BSCRIPT, 'version': version}],
        'dependencies': [{'uuid': RHEAD, 'version': version}, {'module_name': '@minecraft/server', 'version': '2.8.0'}]})
    atlas = {'grassflow_dirt': {'textures': 'textures/blocks/grassflow_dirt'}}
    perms = []
    for c in tiles:
        name = 'grassflow_' + ''.join(map(str, c))
        atlas[name] = {'textures': 'textures/blocks/' + name}
        condition = ' && '.join(f"q.block_state('grassflow:{k}') == {v}" for k,v in zip(KEYS,c))
        material = {'*': {'texture':'grassflow_dirt','render_method':'opaque'},
                    'up': {'texture':name,'render_method':'opaque'}}
        perms.append({'condition': condition, 'components': {'minecraft:material_instances': material}})
    write_json(RP / 'textures/terrain_texture.json', {'resource_pack_name':'grassflow_experiment', 'texture_name':'atlas.terrain',
               'padding':8, 'num_mip_levels':4, 'texture_data':atlas})
    write_json(BP / 'blocks/sample.json', {'format_version':'1.26.30', 'minecraft:block': {
        'description': {'identifier':'grassflow:sample', 'states': {**{f'grassflow:{k}':[0,1,2] for k in KEYS[:4]}, 'grassflow:detail':[0,1,2,3]}},
        'components': {'minecraft:display_name':'Тестовая почва', 'minecraft:geometry':'minecraft:geometry.full_block',
                       'minecraft:material_instances': {'*': {'texture':'grassflow_dirt','render_method':'opaque'},
                                                        'up': {'texture':'grassflow_11110','render_method':'opaque'}},
                       'minecraft:collision_box':True, 'minecraft:selection_box':True,
                       'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.6},
                       'minecraft:destructible_by_explosion': {'explosion_resistance': 0.6}},
        'permutations':perms}})


def make_preview(tiles):
    data = subprocess.check_output(['node', str(ROOT / 'tools/grass_flow_grid.mjs'), '-16', '32'], text=True)
    grid = json.loads(data)
    # Show real source detail, not a synthesized interpretation of the result.
    out = Image.new('RGB', (32*128, 32*128))
    scaled = {key: value.resize((128,128), Image.Resampling.LANCZOS) for key, value in tiles.items()}
    for z, row in enumerate(grid):
        for x, corners in enumerate(row):
            out.paste(scaled[tuple(corners)], (x*128,z*128))
    out.resize((2048,2048), Image.Resampling.LANCZOS).save(ROOT / 'grass-flow-preview.jpg', quality=93, subsampling=0)
    # Example closer view: a region of the very same coordinate map, not an in-game screenshot.
    out.crop((15*128, 20*128, 23*128, 28*128)).save(ROOT / 'grass-flow-preview-close.jpg', quality=94, subsampling=0)
    out.crop((1024, 1024, 3072, 3072)).resize((256, 256), Image.Resampling.LANCZOS).save(RP / 'pack_icon.png')
    Image.open(RP / 'pack_icon.png').save(BP / 'pack_icon.png')


def bytes_pack(folder):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(folder.rglob('*')):
            if file.is_file(): z.write(file, file.relative_to(folder).as_posix())
    return out.getvalue()


def main():
    tiles = get_tiles()
    build_data(tiles)
    make_preview(tiles)
    with zipfile.ZipFile(ROOT / 'grass-flow-experiment.mcaddon', 'w', zipfile.ZIP_STORED) as out:
        out.writestr('grass-flow-resources.mcpack', bytes_pack(RP))
        out.writestr('grass-flow-behavior.mcpack', bytes_pack(BP))
    print('Built 324 textures, separate addon and coordinate-matched preview.')


if __name__ == '__main__': main()
