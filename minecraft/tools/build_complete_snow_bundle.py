#!/usr/bin/env python3
"""Combine the published main resource pack and snow-footprint addon.

The output contains one combined resource pack and one behavior pack. It
preserves the main-pack assets, including ordinary ice, and copies the exact
footprint particle, texture and scripts from the existing addon. Selected PNGs
are losslessly recompressed to stay under GitHub's per-file limit. Distinct bundle UUIDs prevent
silently replacing the user's existing standalone packs. They must not be
activated together: two behavior packs would generate duplicate footprints.
Run from any directory; only Python's standard library is required.
"""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'realistic-dirt.mcpack'
FOOTPRINTS=ROOT/'snow-footprints.mcaddon'
OUTPUT=ROOT/'realistic-snow-complete.mcaddon'
LIMIT=100*1024*1024
RP_UUID='c8c5c07b-11b4-4a7a-bd2c-c01bfc330b56'
RP_MODULE_UUID='f6d52832-f7ec-47e4-bdc3-0af1e104af02'
BP_UUID='794f903e-2d1b-48fe-a080-ce4f08b428fd'
BP_DATA_UUID='7d7ec5ba-5557-4136-8168-8ec16920449a'
BP_SCRIPT_UUID='e7d7008f-1b2e-4bd7-a795-fc70f239738c'
BUNDLE_VERSION=[1,0,3]
ICE_FILE='textures/blocks/ice.png'
ICE_TEXTURE=ROOT/'ice-reference/ice.png'
OPTIMIZED=ROOT/'ice-bundle-optimized'
LOSSLESS_FILES={f'textures/blocks/{name}.png' for name in (
    'amethyst_block','clay','copper_ore','iron_ore','packed_mud','planks_oak','sandstone_normal')}
RESOURCE_FILES={'particles/footprint.json','textures/particle/aegis_snow_footprint.png'}
BEHAVIOR_FILES={'manifest.json','scripts/main.js','scripts/footsteps.js'}


def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def png_semantic_content(data):
    """Return metadata/chunks and raw filtered pixels for a validated PNG.

    Comparing the decompressed IDAT data proves identical scanlines and all
    non-IDAT chunks (including palette, transparency, color info) are kept.
    """
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid PNG signature')
    pos=8; metadata=[]; ids=[]; ended=False
    while pos<len(data):
        if pos+12>len(data):raise ValueError('Truncated PNG chunk')
        n=int.from_bytes(data[pos:pos+4],'big');kind=data[pos+4:pos+8]
        if pos+n+12>len(data):raise ValueError('Truncated PNG data')
        content=data[pos+8:pos+8+n];crc=int.from_bytes(data[pos+8+n:pos+12+n],'big')
        if zlib.crc32(kind+content)&0xffffffff != crc:raise ValueError('Bad PNG CRC')
        if kind==b'IDAT':
            if not ids:metadata.append((b'IDAT',b''))
            ids.append(content)
        else:metadata.append((kind,content))
        pos+=n+12
        if kind==b'IEND':ended=True;break
    if not ended or pos!=len(data) or not ids:raise ValueError('Incomplete PNG')
    return metadata,zlib.decompress(b''.join(ids))


def bundle_terrain(original):
    result=copy.deepcopy(original)
    value={'textures':'textures/blocks/ice'}
    existing=result['texture_data'].get('ice')
    if existing is not None and existing!=value:raise ValueError('Unexpected ice atlas collision')
    result['texture_data']['ice']=value
    return result


def bundle_manifest(original):
    result=copy.deepcopy(original)
    header=result['header']
    header.update(name='Реалистичная земля и трава + следы — ресурсы',
                  description='Основной текстурпак и ресурсы следов; для следов нужен набор поведения из этого комплекта.',
                  uuid=RP_UUID,version=BUNDLE_VERSION,min_engine_version=[1,26,30])
    if len(result['modules'])!=1 or result['modules'][0]['type']!='resources':
        raise ValueError('Unexpected main resource manifest')
    result['modules'][0].update(uuid=RP_MODULE_UUID,version=BUNDLE_VERSION)
    return result


def behavior_manifest(original):
    result=copy.deepcopy(original)
    result['header'].update(name='Реалистичная земля и трава + следы — поведение',
                            uuid=BP_UUID,version=BUNDLE_VERSION)
    modules=result['modules']
    if {m['type'] for m in modules}!={'data','script'} or len(modules)!=2:
        raise ValueError('Unexpected footprint behavior modules')
    for module in modules:
        module['uuid']=BP_DATA_UUID if module['type']=='data' else BP_SCRIPT_UUID
        module['version']=BUNDLE_VERSION
    rp_deps=[d for d in result['dependencies'] if 'uuid' in d]
    if len(rp_deps)!=1:
        raise ValueError('Unexpected footprint resource dependency')
    rp_deps[0].update(uuid=RP_UUID,version=BUNDLE_VERSION)
    return result


def entry(name,data,archive):
    info=zipfile.ZipInfo(name,(2020,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=0o100644 << 16
    archive.writestr(info,data,compresslevel=9)


def copy_stored_file(archive,name,path):
    info=zipfile.ZipInfo(name,(2020,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_STORED
    info.external_attr=0o100644 << 16
    # Stream the 100MB archive rather than duplicating it in memory.
    with archive.open(info,'w',force_zip64=False) as dest, path.open('rb') as source:
        shutil.copyfileobj(source,dest,length=1024*1024)


def main():
    # Keep temporary output on the same filesystem so replace is atomic.
    with tempfile.TemporaryDirectory(prefix='.snow-complete-',dir=ROOT) as temp:
        tmp=Path(temp); rp_file=tmp/'resources.mcpack'; bp_file=tmp/'behavior.mcpack'; final=tmp/'bundle.mcaddon'
        with zipfile.ZipFile(FOOTPRINTS) as addon:
            if set(addon.namelist())!={'snow-footprints-resources.mcpack','snow-footprints-behavior.mcpack'}:
                raise ValueError('Unexpected footprint addon layout')
            rp_data=addon.read('snow-footprints-resources.mcpack')
            bp_data=addon.read('snow-footprints-behavior.mcpack')
        with zipfile.ZipFile(io.BytesIO(rp_data)) as footprint_rp:
            if set(footprint_rp.namelist())!=RESOURCE_FILES|{'manifest.json'}:
                raise ValueError('Unexpected footprint resource files')
            additions={name:footprint_rp.read(name) for name in RESOURCE_FILES}
        with zipfile.ZipFile(BASE) as base, zipfile.ZipFile(rp_file,'w') as rp:
            if base.testzip() is not None or len(set(base.namelist()))!=len(base.namelist()):
                raise ValueError('Invalid or duplicate entries in main pack')
            if set(base.namelist()) & RESOURCE_FILES:
                raise ValueError('Footprint assets already present in main pack; review collision')
            # Older inputs may lack ice; newer main packs contain it. Reject a
            # mismatch rather than silently overwrite a future main-pack tile.
            has_ice=ICE_FILE in base.namelist()
            if has_ice and base.read(ICE_FILE)!=ICE_TEXTURE.read_bytes():
                raise ValueError('Main pack ice differs from the supplied reference; review collision')
            if not LOSSLESS_FILES <= set(base.namelist()):
                raise ValueError('Missing original files for lossless recompression')
            for info in base.infolist():
                payload=base.read(info.filename)
                if info.filename=='manifest.json':payload=json_bytes(bundle_manifest(json.loads(payload)))
                elif info.filename=='textures/terrain_texture.json':payload=json_bytes(bundle_terrain(json.loads(payload)))
                elif info.filename in LOSSLESS_FILES:
                    optimized=(OPTIMIZED/info.filename).read_bytes()
                    if png_semantic_content(payload)!=png_semantic_content(optimized):
                        raise ValueError(f'Lossless PNG mismatch: {info.filename}')
                    payload=optimized
                # Preserve compression choice and file metadata of main pack.
                rp.writestr(info,payload,compress_type=info.compress_type,compresslevel=9)
            for name in sorted(RESOURCE_FILES):entry(name,additions[name],rp)
            if not has_ice:entry(ICE_FILE,ICE_TEXTURE.read_bytes(),rp)
        with zipfile.ZipFile(io.BytesIO(bp_data)) as old, zipfile.ZipFile(bp_file,'w') as bp:
            if set(old.namelist())!=BEHAVIOR_FILES:
                raise ValueError('Unexpected footprint behavior files')
            for name in sorted(BEHAVIOR_FILES):
                payload=old.read(name)
                if name=='manifest.json':payload=json_bytes(behavior_manifest(json.loads(payload)))
                entry(name,payload,bp)
        with zipfile.ZipFile(final,'w') as out:
            copy_stored_file(out,'realistic-snow-resources.mcpack',rp_file)
            copy_stored_file(out,'realistic-snow-behavior.mcpack',bp_file)
        if final.stat().st_size >= LIMIT:
            raise ValueError(f'Combined addon exceeds GitHub single-file limit: {final.stat().st_size}')
        with zipfile.ZipFile(final) as check:
            if check.testzip() is not None:raise ValueError('Corrupt combined addon')
        final.replace(OUTPUT)
    print(f'Built {OUTPUT}: {OUTPUT.stat().st_size} bytes (limit {LIMIT})')

if __name__=='__main__':main()
