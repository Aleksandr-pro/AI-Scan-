#!/usr/bin/env python3
"""Build isolated 3D melon experiment from the user's generated mesh and texture.

Bedrock custom blocks use cuboid geometry, so this is a stepped approximation,
not a direct polymesh import. Requires Pillow. Never alters the main pack.
"""
import io
import json
import math
from pathlib import Path
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'melon-experiment'
REF = ROOT / 'melon-reference'
RP, BP, REC = (BASE / n for n in ('resources', 'behavior', 'recovery'))
VERSION = [1, 0, 0]
RP_ID = '7e5e5c87-9fa0-4f7a-bea4-38c67b37019b'
BP_ID = 'c739eb07-7ab4-4860-8085-548009f697f0'
REC_ID = '3a6fff4a-de80-48d3-ad33-4b3970eda6cd'


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def geometry_and_atlas():
    mesh = json.loads((REF / 'generated-mesh.json').read_text())
    texture = Image.open(REF / 'generated-texture.png').convert('RGBA')
    cols, rows = mesh['cols'], mesh['melonRows']
    positions = mesh['positions']
    rings = []
    for j in range(rows):
        pts = [positions[3*(j*cols+i):3*(j*cols+i)+3] for i in range(cols-1)]
        rings.append((pts[0][0]*16, min(p[1]*16 for p in pts), max(p[1]*16 for p in pts), max(abs(p[2]*16) for p in pts)))
    # One slice per interval in the original default mesh: 8 stepped cuboids.
    atlas = Image.new('RGBA', (256, 256), (0, 0, 0, 255))
    cubes = []
    faces = ('north', 'south', 'west', 'east', 'up', 'down')
    for j in range(rows-1):
        left, right = rings[j], rings[j+1]
        x0, x1 = left[0], right[0]
        # interpolate the generator's ring silhouette; narrowed slightly at poles
        y0 = max(0, (left[1]+right[1])/2)
        y1 = min(16, (left[2]+right[2])/2)
        rz = (left[3]+right[3])/2
        if x1-x0 < 0.01 or y1-y0 < 0.01 or rz < 0.01:
            continue
        uv = {}
        for k, face in enumerate(faces):
            # Each face gets a separate 32px tile sampled from the user's atlas.
            tx, ty = j*32, k*32
            uv[face] = {'uv': [tx, ty], 'uv_size': [32, 32]}
            for py in range(32):
                for px in range(32):
                    a, b = (px+.5)/32, (py+.5)/32
                    x = x0 + a*(x1-x0)
                    y = y1 - b*(y1-y0)
                    z = -rz if face == 'north' else rz
                    if face in ('east', 'west'):
                        x = x1 if face == 'east' else x0
                        z = (a*2-1)*rz
                    elif face in ('up', 'down'):
                        y = y1 if face == 'up' else y0
                        z = (b*2-1)*rz
                    angle = math.atan2(z / (rz or 1), (y-(y0+y1)/2) / ((y1-y0)/2))
                    u = (angle / (2*math.pi)) % 1
                    # generator's v runs from 0.125 to 1 along the long axis
                    v = .125 + .875*max(0, min(1, (x-rings[0][0])/(rings[-1][0]-rings[0][0])))
                    atlas.putpixel((tx+px,ty+py), texture.getpixel((int(u*64)%64, max(0,min(63,int((1-v)*64))))))
        cubes.append({'origin': [round(x0,4),round(y0,4),round(-rz,4)],
                      'size': [round(x1-x0,4),round(y1-y0,4),round(rz*2,4)],'uv': uv})
    # Stem colour is sampled from the generator's bottom texture band.
    for y in range(192,224):
        for x in range(32): atlas.putpixel((x,y), texture.getpixel((x*2, 60)))
    cubes.append({'origin': [-7.9, 5.05, -.35], 'size': [1.3, .7, .7], 'uv': [0,192]})
    return {'format_version':'1.12.0','minecraft:geometry':[{'description':{
        'identifier':'geometry.aimelon.fruit','texture_width':256,'texture_height':256,
        'visible_bounds_width':2,'visible_bounds_height':2,'visible_bounds_offset':[0,.5,0]},
        'bones':[{'name':'melon','pivot':[0,0,0],'cubes':cubes}]}]}, atlas


def manifest(name, uid, modules, description, deps=None):
    result={'format_version':2,'header':{'name':name,'description':description,'uuid':uid,'version':VERSION,'min_engine_version':[1,26,30]},'modules':modules}
    if deps is not None: result['dependencies']=deps
    return result


def module(kind, uid): return {'type':kind,'uuid':uid,'version':VERSION}


def pack(directory):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                info=zipfile.ZipInfo(path.relative_to(directory).as_posix(),(2020,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644 << 16
                z.writestr(info,path.read_bytes(),compresslevel=9)
    return stream.getvalue()


def main():
    geom, atlas = geometry_and_atlas()
    dump(RP/'models/blocks/melon.geo.json',geom)
    (RP/'textures/blocks').mkdir(parents=True,exist_ok=True)
    atlas.save(RP/'textures/blocks/aimelon_fruit.png',optimize=True)
    dump(RP/'textures/terrain_texture.json',{'resource_pack_name':'aimelon','texture_name':'atlas.terrain','texture_data':{'aimelon_fruit':{'textures':'textures/blocks/aimelon_fruit'}}})
    dump(RP/'manifest.json',manifest('3D арбуз — ресурсы (эксперимент)',RP_ID,[module('resources','89fcb742-b5e1-48db-8822-7c76ec6a409d')],'Ресурсы экспериментального арбуза'))
    block={'format_version':'1.26.30','minecraft:block':{'description':{'identifier':'aimelon:fruit'},'components':{
        'minecraft:display_name':'3D арбуз (эксперимент)', 'minecraft:geometry':'geometry.aimelon.fruit',
        'minecraft:material_instances':{'*':{'texture':'aimelon_fruit','render_method':'opaque'}},
        'minecraft:collision_box':{'origin':[-8,0,-8],'size':[16,16,16]},
        'minecraft:selection_box':{'origin':[-8,0,-8],'size':[16,16,16]},
        'minecraft:destructible_by_mining':{'seconds_to_destroy':1},
        'minecraft:destructible_by_explosion':{'explosion_resistance':1},
        'minecraft:loot':'loot_tables/blocks/melon.json'}}}
    loot={'pools':[{'rolls':1,'entries':[{'type':'item','name':'minecraft:melon','weight':1,'functions':[{'function':'set_count','count':{'min':3,'max':7}}]}]}]}
    for directory in (BP,REC):
        dump(directory/'blocks/melon.json',block)
        dump(directory/'loot_tables/blocks/melon.json',loot)
    dependencies=[{'uuid':RP_ID,'version':VERSION},{'module_name':'@minecraft/server','version':'2.8.0'}]
    for directory,name,uid,data_id,script_id,desc in (
        (BP,'3D арбуз — автоматическая замена (эксперимент)',BP_ID,'66245e2e-2274-4dec-8994-7bee50d1780b','06e6fba0-0e11-4405-b497-1dca2bf7d3ab','Меняет обычные арбузы рядом с игроком. Только копия мира.'),
        (REC,'3D арбуз — восстановление (эксперимент)',REC_ID,'a12cb28a-6c84-409d-bcfa-f18290069522','50fe2df2-8216-4087-8522-acb6118e4e4a','Возвращает экспериментальные арбузы в обычные рядом с игроком.')):
        script=module('script',script_id); script.update(language='javascript',entry='scripts/main.js')
        dump(directory/'manifest.json',manifest(name,uid,[module('data',data_id),script],desc,dependencies))
    target=ROOT/'realistic-melon-experiment.mcaddon'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_STORED) as z:
        for name,path in [('melon-resources.mcpack',RP),('melon-auto.mcpack',BP),('melon-recovery.mcpack',REC)]:
            info=zipfile.ZipInfo(name,(2020,1,1,0,0,0)); info.external_attr=0o100644<<16
            z.writestr(info,pack(path))
    print('Built',target,target.stat().st_size,'bytes')

if __name__=='__main__': main()
