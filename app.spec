# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('X:\\ffmpeg-2026-04-01-git-eedf8f0165-full_build\\ffmpeg-2026-04-01-git-eedf8f0165-full_build\\bin\\ffmpeg.exe', '.'), ('C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe', '.'), ('C:\\Users\\Admin\\AppData\\Local\\Programs\\ExifTool\\ExifTool.exe', '.')],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
