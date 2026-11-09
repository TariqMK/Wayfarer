# PyInstaller build: one self-contained .exe on Windows, one file on Linux, and one .app bundle on macOS.
import sys

a = Analysis(
    ["wayfarer/__main__.py"],
    pathex=["."],
    datas=[("wayfarer/ui", "wayfarer/ui")],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Wayfarer", console=False, target_arch="arm64")
    coll = COLLECT(exe, a.binaries, a.datas, name="Wayfarer")
    app = BUNDLE(coll, name="Wayfarer.app", bundle_identifier="com.tariqmk.wayfarer")
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Wayfarer", console=False, upx=False)
