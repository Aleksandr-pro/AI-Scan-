#!/usr/bin/env python3
"""Bundle the existing full texture pack and the automatic grass-flow addon.

The output is intentionally excluded from Git due to GitHub's 100 MiB limit.
The automatic behavior really changes blocks; read the safety instructions.
"""
from pathlib import Path
import tempfile
import zipfile
from build_complete_grassflow_bundle import transform_pack

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'realistic-complete-automatic.mcaddon'

def main():
    with tempfile.TemporaryDirectory(prefix='grassflow-full-auto-') as temp:
        base=Path(temp)/'realistic-dirt.mcpack'
        transform_pack(ROOT/'realistic-dirt.mcpack',base,'base')
        with zipfile.ZipFile(ROOT/'grass-flow-automatic.mcaddon') as auto, zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_STORED,allowZip64=True) as out:
            out.write(base,'realistic-dirt.mcpack')
            for name in auto.namelist():
                out.writestr(name,auto.read(name))
    print(f'Built {OUTPUT} ({OUTPUT.stat().st_size/1024**2:.1f} MiB).')

if __name__=='__main__':main()
