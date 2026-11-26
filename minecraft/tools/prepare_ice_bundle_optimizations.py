#!/usr/bin/env python3
"""Losslessly recompress selected original PNGs to make room for ordinary ice.

Run from the repository root with the Python zopfli package installed. The
standalone texture pack is read-only; regenerated PNGs are used only in the
combined bundle. All PNG metadata and decompressed IDAT bytes are verified.
"""
import os
from pathlib import Path
import tempfile
import zipfile
from build_complete_snow_bundle import BASE, LOSSLESS_FILES, OPTIMIZED, png_semantic_content
from optimize_png_lossless import optimize


def main():
    with zipfile.ZipFile(BASE) as source:
        for name in sorted(LOSSLESS_FILES):
            original=source.read(name)
            target=OPTIMIZED/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent,delete=False,suffix='.tmp') as tmp:
                temp=Path(tmp.name)
                tmp.write(original)
            try:
                optimize(temp)
                if png_semantic_content(temp.read_bytes())!=png_semantic_content(original):
                    raise ValueError(f'Pixel or metadata mismatch: {name}')
                os.replace(temp,target)
            finally:
                temp.unlink(missing_ok=True)

if __name__=='__main__':main()
