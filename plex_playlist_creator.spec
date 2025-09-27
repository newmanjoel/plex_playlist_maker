# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_all

stdatas, binaries, hiddenimports = collect_all('streamlit')

import glob
import os


# Collect all .py files in the project folder (except driver.py)
project_dir = os.path.abspath(r"/home/joel/Desktop/plex_playlists/plex_playlist_maker/web_src")
datas = [(f, ".") for f in glob.glob(os.path.join(project_dir, "*.py")) if not f.endswith("driver.py")]
datas.extend(stdatas)


a = Analysis(
    ['web_src/driver.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('/usr/bin/python3.13', None, 'OPTION')],
    exclude_binaries=True,
    name='plex_playlist_creator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='plex_playlist_creator',
)
