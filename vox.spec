# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'vox',
        'vox.service',
        'vox.api',
        'vox.config',
        'vox.ui',
        'vox.notifications',
    ],
    hookspath=[],
    hooksconfig={},
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
    name='Vox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
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
    name='Vox',
)

app = BUNDLE(
    coll,
    name='Vox.app',
    icon=None,
    bundle_identifier='com.voxapp.rewrite',
    info_plist={
        'CFBundleName': 'Vox',
        'CFBundleDisplayName': 'Vox',
        'CFBundleIdentifier': 'com.voxapp.rewrite',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
        'NSServices': [
            {
                'NSMessage': 'fixGrammarService',
                'NSMenuItem': {'default': 'Rewrite with Vox'},
                'NSPortName': 'Vox',
                'NSSendTypes': ['public.utf8-plain-text'],
                'NSReturnTypes': ['public.utf8-plain-text'],
                'NSRestrictedContext': True,
            },
            {
                'NSMessage': 'fixGrammarService',
                'NSMenuItem': {'default': 'Rewrite with Vox/Fix Grammar'},
                'NSPortName': 'Vox',
                'NSSendTypes': ['public.utf8-plain-text'],
                'NSReturnTypes': ['public.utf8-plain-text'],
            },
            {
                'NSMessage': 'professionalService',
                'NSMenuItem': {'default': 'Rewrite with Vox/Professional'},
                'NSPortName': 'Vox',
                'NSSendTypes': ['public.utf8-plain-text'],
                'NSReturnTypes': ['public.utf8-plain-text'],
            },
            {
                'NSMessage': 'conciseService',
                'NSMenuItem': {'default': 'Rewrite with Vox/Concise'},
                'NSPortName': 'Vox',
                'NSSendTypes': ['public.utf8-plain-text'],
                'NSReturnTypes': ['public.utf8-plain-text'],
            },
            {
                'NSMessage': 'friendlyService',
                'NSMenuItem': {'default': 'Rewrite with Vox/Friendly'},
                'NSPortName': 'Vox',
                'NSSendTypes': ['public.utf8-plain-text'],
                'NSReturnTypes': ['public.utf8-plain-text'],
            },
        ],
    },
)
