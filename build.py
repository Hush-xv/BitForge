"""
BitForge — PyInstaller 打包脚本
用法: python build_bitforge.py
"""

import os, shutil, subprocess, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(SCRIPT_DIR, "bitforge.py")
DIST = os.path.join(SCRIPT_DIR, "dist")
WORK = os.path.join(SCRIPT_DIR, "build_bitforge")

for d in [DIST, WORK]:
    if os.path.exists(d): shutil.rmtree(d)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile", "--windowed",
    "--name", "BitForge",
    "--distpath", DIST,
    "--workpath", WORK,
    "--collect-all", "siui",
    "--collect-all", "PyQt5",
    MAIN,
]

print(f"[BUILD] BitForge...")
result = subprocess.run(cmd, cwd=SCRIPT_DIR)

if result.returncode == 0:
    exe = os.path.join(DIST, "BitForge.exe")
    if os.path.exists(exe):
        mb = os.path.getsize(exe) / 1024 / 1024
        print(f"\n[OK]  Build complete!")
        print(f"     EXE: {exe}")
        print(f"     Size: {mb:.1f} MB")
    else:
        print(f"\n[WARN] EXE not found")
else:
    print(f"\n[FAIL] exit code {result.returncode}")
    sys.exit(1)
