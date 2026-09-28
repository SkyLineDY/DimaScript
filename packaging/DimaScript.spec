# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
datas, binaries = [], []
hiddenimports = ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox']
datas += copy_metadata('huggingface-hub')
for package in ['faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime', 'av']:
    found = collect_all(package)
    datas += found[0]
    binaries += found[1]
    hiddenimports += found[2]

a = Analysis([str(root / 'src' / 'app.py')], pathex=[str(root / 'src')],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
# Recognition uses CPU int8. Do not redistribute an unused NVIDIA runtime.
a.binaries = [entry for entry in a.binaries if 'cudnn' not in entry[0].lower()]
a.datas = [entry for entry in a.datas if 'cudnn' not in entry[0].lower()]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DimaScript', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False, icon=str(root / 'assets' / 'app.ico'),
    version=str(root / 'packaging' / 'version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DimaScript')
