# -*- mode: python ; coding: utf-8 -*-
"""GifPet for macOS — PyInstaller spec (produces GifPet.app bundle)"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('default_pet', 'default_pet')],
    hiddenimports=[
        'AppKit', 'Foundation', 'Cocoa',
        'pynput.keyboard._darwin', 'pynput.mouse._darwin',
        'pystray._darwin',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GifPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GifPet',
)

app = BUNDLE(
    coll,
    name='GifPet.app',
    icon=None,
    bundle_identifier='com.gifpet.app',
    version='1.4.0',
    info_plist={
        # Dock 아이콘 숨기기 (메뉴바/트레이 앱)
        'LSUIElement': True,
        # pynput 접근성 권한 안내
        'NSAccessibilityUsageDescription': (
            'GifPet이 키보드 입력 감지를 위해 접근성 권한이 필요합니다.'
        ),
        'CFBundleName': 'GifPet',
        'CFBundleDisplayName': 'GifPet',
        'CFBundleShortVersionString': '1.4.0',
        'NSHighResolutionCapable': True,
    },
)
