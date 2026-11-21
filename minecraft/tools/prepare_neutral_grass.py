#!/usr/bin/env python3
"""Neutralize grass biome tint, retaining existing textures and water packs.

Two white grass colormaps cover climate and swamp maps. Vanilla client biomes
with explicit fixed grass colors or dark-forest shading also need narrow,
full-file overrides. The optional, tiny water-compat pack copies those same
biomes from the user's existing three-photo water pack so that its water
settings aren't lost when both packs are enabled (compat pack must be highest).
No leaves/foliage colormaps, block textures, scripts, or world data are changed.
"""
from pathlib import Path
import json
import zipfile
from PIL import Image

ROOT=Path('minecraft')
VANILLA=ROOT/'vanilla-client-biomes-1.26.30.5'
MAIN=ROOT/'realistic-dirt'
WATER=ROOT/'realistic-water-three-photos'
COMPAT=ROOT/'grass-water-compat'
ARCHIVE=ROOT/'grass-water-compat.mcpack'


def needs_override(biome):
    grass=biome['minecraft:client_biome']['components'].get('minecraft:grass_appearance',{})
    return isinstance(grass.get('color'),str) or grass.get('grass_is_shaded',False)


def neutralize(biome):
    components=biome['minecraft:client_biome']['components']
    grass=components.setdefault('minecraft:grass_appearance',{})
    grass['color']='#FFFFFF'
    # In dark forest the separate shading flag also darkens the grass tint.
    if 'grass_is_shaded' in grass:grass['grass_is_shaded']=False
    return biome


def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    maps=MAIN/'textures/colormap'
    maps.mkdir(parents=True,exist_ok=True)
    for name in ('grass','swamp_grass'):
        Image.new('RGB',(256,256),'white').save(maps/(name+'.png'),optimize=True)
    originals=sorted(VANILLA.glob('*.client_biome.json'))
    if len(originals)!=88:raise ValueError(f'Expected 88 pinned sample biomes, got {len(originals)}')
    names=[]
    for src in originals:
        vanilla=json.loads(src.read_text(encoding='utf-8'))
        if not needs_override(vanilla):continue
        names.append(src.name)
        dump(MAIN/'biomes'/src.name,neutralize(vanilla))
        # Keep every water-pack component (including white tint and opacity).
        water=json.loads((WATER/'biomes'/src.name).read_text(encoding='utf-8'))
        dump(COMPAT/'biomes'/src.name,neutralize(water))
    if len(names)!=9:raise ValueError(f'Unexpected fixed-color/shaded biome set: {names}')
    manifest={'format_version':2,'header':{
        'name':'Фото-трава + вода: совместимость',
        'description':'Нейтральная трава и настройки воды из пакета трёх фотографий',
        'uuid':'b6b4f173-66b9-4967-bd0d-0b0414cef357','version':[1,0,0],
        'min_engine_version':[1,26,30]},'modules':[{
        'type':'resources','uuid':'fd8aec1a-7ca7-4ad1-ae48-38f1461118f4','version':[1,0,0]}]}
    dump(COMPAT/'manifest.json',manifest)
    expected={'manifest.json'}|{'biomes/'+name for name in names}
    found={p.relative_to(COMPAT).as_posix() for p in COMPAT.rglob('*') if p.is_file()}
    if found!=expected:raise ValueError(f'Unexpected compatibility files: {found^expected}')
    with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(expected):z.write(COMPAT/name,name)
    print(f'Prepared neutral grass maps, {len(names)} exceptional biomes and {ARCHIVE}.')


if __name__=='__main__':main()
