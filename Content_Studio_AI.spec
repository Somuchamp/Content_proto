# -*- mode: python ; coding: utf-8 -*-
import os
import praw
import pkgutil
import google.ads.googleads

praw_ini = os.path.join(os.path.dirname(praw.__file__), 'praw.ini')

# Dynamically gather all submodules of google-ads to resolve PyInstaller dynamic import issues
google_ads_imports = ['google.ads.googleads']
try:
    for loader, name, ispkg in pkgutil.walk_packages(google.ads.googleads.__path__, google.ads.googleads.__name__ + '.'):
        google_ads_imports.append(name)
except Exception:
    pass

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[(praw_ini, 'praw')],
    hiddenimports=[
        'praw', 
        'cloudscraper', 
        'googleapiclient', 
        'pandas', 
        'openai', 
        'pydantic_settings', 
        'apscheduler', 
        'app', 
        'app.models', 
        'app.storage', 
        'app.services', 
        'app.api', 
        'app.api.routes', 
        'app.services.dataforseo_service',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'bs4',
        'dotenv',
        'requests',
    ] + google_ads_imports,
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
    name='Content_Studio_AI',
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
    icon=['logo.ico'],
)
