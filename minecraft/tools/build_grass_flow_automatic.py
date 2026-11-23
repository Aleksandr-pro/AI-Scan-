#!/usr/bin/env python3
"""Build automatic, limited and journalled grass-flow behavior; no world commands.

Produces a small standalone addon. See GRASS-FLOW-AUTOMATIC-README.md.
This changes real blocks and has NOT been validated in Minecraft.
"""
from pathlib import Path
import io, json, zipfile

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT/'grass-flow-automatic'
FLOW = ROOT/'grass-flow-experiment.mcaddon'
RP_UUID = '61b4cb0f-a39f-4c77-8510-aec0df8745b7'
RP_MODULE = '3d21a3ba-259a-4bf5-af72-8f08227138d3'
AUTO_UUID, AUTO_DATA, AUTO_SCRIPT = 'f2f70361-baa6-4464-80ad-6229b6f7b47b', 'a64a669a-4598-4335-8e89-d27be894ebc9', 'cda7b8e7-41f4-4c16-b251-2d76686b3a18'
RESTORE_UUID, RESTORE_DATA, RESTORE_SCRIPT = 'faa178ca-b0f4-49a9-88ce-8a19cc86dcc5', '6a9dcf1a-9d3c-4c9b-a953-aa7bebb61426', 'f8f359cf-f92a-4bf7-b2cc-5de4528b7e83'
RESUME_UUID, RESUME_DATA, RESUME_SCRIPT = 'e5db27ff-c08c-4599-8c70-bd9163626ef0', '097145f6-e701-49c9-a1f2-cbfabd44c14e', '3f9387a5-5eb9-417b-9d85-96d5e348f293'
VER = [1, 0, 2]


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def manifest(name, desc, header, module, script, dep):
    return {'format_version':2, 'header':{'name':name, 'description':desc, 'uuid':header,
            'version':VER, 'min_engine_version':[1,26,30]},
            'modules':[{'type':'data','uuid':module,'version':VER},
                       {'type':'script','language':'javascript','entry':'scripts/main.js','uuid':script,'version':VER}],
            'dependencies':[{'uuid':dep,'version':VER}, {'module_name':'@minecraft/server','version':'2.8.0'}]}


def pack_bytes(path):
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for p in sorted(path.rglob('*')):
            if p.is_file():out.write(p,p.relative_to(path).as_posix())
    return mem.getvalue()


def update_resource(data):
    result=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as original, zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        manifest=json.loads(original.read('manifest.json'))
        assert manifest['header']['uuid']=='07e733e9-d5e9-4133-b826-29571da21290'
        manifest['header'].update({'uuid':RP_UUID,'version':VER,
                                   'name':'Живая почва — автоматические ресурсы',
                                   'description':'Ресурсы автоматической живой почвы.'})
        assert len(manifest['modules'])==1
        manifest['modules'][0].update({'uuid':RP_MODULE,'version':VER})
        for f in original.infolist():
            out.writestr(f, (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode() if f.filename=='manifest.json' else original.read(f),compresslevel=9)
    return result.getvalue()


def main():
    bp, restore, resume = DIR/'behavior', DIR/'restore', DIR/'resume'
    write(bp/'manifest.json',manifest('Живая почва — автоматически', 'Осторожно: временно меняет до 256 открытых блоков дёрна. Только копия мира.',AUTO_UUID,AUTO_DATA,AUTO_SCRIPT,RP_UUID))
    write(restore/'manifest.json',manifest('Живая почва — восстановление', 'Включить вместе с автоматическим набором, чтобы вернуть блоки без команд.',RESTORE_UUID,RESTORE_DATA,RESTORE_SCRIPT,AUTO_UUID))
    write(resume/'manifest.json',manifest('Живая почва — возобновление', 'Разрешает автоматический режим после полного восстановления.',RESUME_UUID,RESUME_DATA,RESUME_SCRIPT,AUTO_UUID))
    source=json.loads((ROOT/'grass-flow-experiment/behavior/blocks/sample.json').read_text())
    block=source['minecraft:block']
    block['description']['identifier']='grassflow:auto_terrain'
    block['components']['minecraft:display_name']='Живая почва (авто)'
    block['components']['minecraft:movable']={'movement_type':'immovable'}
    block['components']['minecraft:loot']='loot_tables/blocks/auto_terrain.json'
    write(bp/'blocks/auto_terrain.json',source)
    write(bp/'loot_tables/blocks/auto_terrain.json', {'pools':[{'rolls':1,'entries':[{'type':'item','name':'minecraft:dirt','weight':1}]}]})
    with zipfile.ZipFile(FLOW) as old:
        resource=update_resource(old.read('grass-flow-resources.mcpack'))
    with zipfile.ZipFile(ROOT/'grass-flow-automatic.mcaddon','w',zipfile.ZIP_STORED) as out:
        out.writestr('grass-flow-resources.mcpack',resource)
        out.writestr('grass-flow-automatic.mcpack',pack_bytes(bp))
        out.writestr('grass-flow-restore.mcpack',pack_bytes(restore))
        out.writestr('grass-flow-resume.mcpack',pack_bytes(resume))
    print('Built automatic addon; does not claim vanilla grass behavior parity.')

if __name__=='__main__':main()
