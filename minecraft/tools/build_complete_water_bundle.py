#!/usr/bin/env python3
"""Integrate three-photo water and grass compatibility into the complete bundle.

The original water PNGs and all 16 animation frames are copied without changes.
Only the nine overlapping biome JSON files need a merge. This intentionally
creates a >100 MiB file, which is distributed as a GitHub Release asset rather
than a Git blob. No third-party dependencies; run from any directory.
"""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from build_complete_snow_bundle import (ROOT, OUTPUT as OLD_BUNDLE, RP_UUID, BP_UUID,
    ICE_FILE, ICE_TEXTURE, copy_stored_file, entry, json_bytes)

WATER=ROOT/'realistic-water-three-photos.mcpack'
COMPAT=ROOT/'grass-water-compat.mcpack'
OUTPUT=ROOT/'realistic-complete-water.mcaddon'
VERSION=[1,0,5]
OLD_VERSION=[1,0,4]
RP='realistic-snow-resources.mcpack'
BP='realistic-snow-behavior.mcpack'
WATER_TEXTURES={'textures/blocks/water_still_grey.png','textures/blocks/water_flow_grey.png'}


def validate_water_and_compat(base,water,compat):
    """Fail closed on unexpected content or collisions; return output additions."""
    for z in (base,water,compat):
        if z.testzip() is not None or len(z.namelist())!=len(set(z.namelist())):
            raise ValueError('Corrupt archive or duplicate entries')
    all_biomes={'biomes/'+p.name for p in (ROOT/'vanilla-client-biomes-1.26.30.5').glob('*.client_biome.json')}
    if len(all_biomes)!=88 or set(water.namelist())!={'manifest.json'}|WATER_TEXTURES|all_biomes:
        raise ValueError('Unexpected water resources; review before combining')
    overlap=(set(base.namelist()) & (all_biomes|WATER_TEXTURES))
    if len(overlap)!=9 or not overlap<=all_biomes or set(compat.namelist())!=overlap|{'manifest.json'}:
        raise ValueError('Unexpected biome or texture collision')
    data={name:water.read(name) for name in all_biomes|WATER_TEXTURES}
    for name in overlap:
        b=json.loads(base.read(name)); w=json.loads(data[name]); c=json.loads(compat.read(name))
        bc=b['minecraft:client_biome']['components']
        wc=w['minecraft:client_biome']['components']
        if 'minecraft:grass_appearance' not in bc or 'minecraft:water_appearance' not in wc:
            raise ValueError(f'Missing grass or water settings: {name}')
        expected=copy.deepcopy(w)
        expected['minecraft:client_biome']['components']['minecraft:grass_appearance']=copy.deepcopy(bc['minecraft:grass_appearance'])
        if c!=expected:
            raise ValueError(f'Compatibility biome is not an exact grass/water merge: {name}')
        # Check that no unrelated base settings are silently discarded.
        without_special=lambda x:{k:v for k,v in x.items() if k not in ('minecraft:grass_appearance','minecraft:water_appearance')}
        if without_special(bc)!=without_special(wc):
            raise ValueError(f'Unrelated biome settings differ: {name}')
        base_meta=copy.deepcopy(b);water_meta=copy.deepcopy(w)
        base_meta['minecraft:client_biome']['components']={}
        water_meta['minecraft:client_biome']['components']={}
        if base_meta!=water_meta:raise ValueError(f'Biome identity differs: {name}')
        data[name]=compat.read(name)
    return data,overlap


def updated_manifest(payload,kind):
    result=json.loads(payload)
    if result['header']['uuid']!=(RP_UUID if kind=='rp' else BP_UUID) or result['header']['version']!=OLD_VERSION:
        raise ValueError(f'Unexpected prior {kind} manifest')
    if not all(m['version']==OLD_VERSION for m in result['modules']):raise ValueError('Old module version mismatch')
    result['header']['version']=VERSION
    result['header']['name']='Реалистичная земля + вода + следы — '+('ресурсы' if kind=='rp' else 'поведение')
    if kind=='rp':result['header']['description']='Основной текстурпак, вода и ресурсы следов; для следов включите поведение комплекта.'
    for m in result['modules']:m['version']=VERSION
    if kind=='bp':
        deps=[d for d in result['dependencies'] if d.get('uuid')==RP_UUID]
        if len(deps)!=1 or deps[0].get('version')!=OLD_VERSION:raise ValueError('Unexpected resource dependency')
        deps[0]['version']=VERSION
    return json_bytes(result)


def extract(outer,name,dest):
    with outer.open(name) as src,dest.open('wb') as out:shutil.copyfileobj(src,out,length=1024*1024)


def build():
    with tempfile.TemporaryDirectory(prefix='.complete-water-',dir=ROOT) as directory:
        tmp=Path(directory); oldrp=tmp/'old-rp.mcpack'; oldbp=tmp/'old-bp.mcpack'
        newrp=tmp/'new-rp.mcpack'; newbp=tmp/'new-bp.mcpack'; result=tmp/'result.mcaddon'
        with zipfile.ZipFile(OLD_BUNDLE) as old:
            if set(old.namelist())!={RP,BP} or old.testzip() is not None:raise ValueError('Unexpected old bundle')
            extract(old,RP,oldrp);extract(old,BP,oldbp)
        with zipfile.ZipFile(oldrp) as base,zipfile.ZipFile(WATER) as water,zipfile.ZipFile(COMPAT) as compat,zipfile.ZipFile(newrp,'w') as rp:
            if base.read(ICE_FILE)!=ICE_TEXTURE.read_bytes():raise ValueError('Old bundle does not contain current ice')
            water_files,overlap=validate_water_and_compat(base,water,compat)
            for info in base.infolist():
                name=info.filename
                payload=updated_manifest(base.read(name),'rp') if name=='manifest.json' else water_files[name] if name in overlap else base.read(name)
                rp.writestr(info,payload,compress_type=info.compress_type,compresslevel=9)
            for name in sorted(set(water_files)-overlap):entry(name,water_files[name],rp)
        with zipfile.ZipFile(oldbp) as old,zipfile.ZipFile(newbp,'w') as bp:
            if old.testzip() is not None:raise ValueError('Bad old behavior pack')
            for info in old.infolist():
                data=updated_manifest(old.read(info.filename),'bp') if info.filename=='manifest.json' else old.read(info.filename)
                bp.writestr(info,data,compress_type=info.compress_type,compresslevel=9)
        with zipfile.ZipFile(result,'w') as out:
            copy_stored_file(out,RP,newrp);copy_stored_file(out,BP,newbp)
        with zipfile.ZipFile(result) as check:
            if check.testzip() is not None:raise ValueError('Corrupt output')
        result.replace(OUTPUT)
    print(f'Built {OUTPUT}: {OUTPUT.stat().st_size} bytes')

if __name__=='__main__':build()
