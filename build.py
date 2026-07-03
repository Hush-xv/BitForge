"""
BitForge — PyInstaller 打包脚本
用法:
    python build.py              # 目录模式 BitForge_Portable/（启动快）
    python build.py --portable   # 单 exe BitForge.exe（方便分发，启动稍慢）
"""
import os, shutil, subprocess, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(SCRIPT_DIR, "bitforge.py")
ICON = os.path.join(SCRIPT_DIR, "bitforge.ico")
DIST = os.path.join(SCRIPT_DIR, "dist")
WORK = os.path.join(SCRIPT_DIR, "build_bitforge")

portable = "--portable" in sys.argv
FOLDER_NAME = "BitForge"

for d in [DIST, WORK]:
    if os.path.exists(d): shutil.rmtree(d)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile" if portable else "--onedir",
    "--windowed",
    "--name", "BitForge",
    "--distpath", DIST,
    "--workpath", WORK,
    f"--icon={ICON}",
    "--collect-all", "siui",
    "--collect-all", "PyQt5",
    "--exclude-module", "PyQt5.Qt3DCore",
    "--exclude-module", "PyQt5.Qt3DInput",
    "--exclude-module", "PyQt5.Qt3DLogic",
    "--exclude-module", "PyQt5.Qt3DRender",
    "--exclude-module", "PyQt5.QtBluetooth",
    "--exclude-module", "PyQt5.QtDBus",
    "--exclude-module", "PyQt5.QtDesigner",
    "--exclude-module", "PyQt5.QtHelp",
    "--exclude-module", "PyQt5.QtLocation",
    "--exclude-module", "PyQt5.QtMultimedia",
    "--exclude-module", "PyQt5.QtMultimediaWidgets",
    "--exclude-module", "PyQt5.QtNfc",
    "--exclude-module", "PyQt5.QtOpenGL",
    "--exclude-module", "PyQt5.QtPositioning",
    "--exclude-module", "PyQt5.QtPrintSupport",
    "--exclude-module", "PyQt5.QtQml",
    "--exclude-module", "PyQt5.QtQuick",
    "--exclude-module", "PyQt5.QtQuick3D",
    "--exclude-module", "PyQt5.QtQuickWidgets",
    "--exclude-module", "PyQt5.QtRemoteObjects",
    "--exclude-module", "PyQt5.QtSensors",
    "--exclude-module", "PyQt5.QtSerialPort",
    "--exclude-module", "PyQt5.QtSql",
    "--exclude-module", "PyQt5.QtTest",
    "--exclude-module", "PyQt5.QtTextToSpeech",
    "--exclude-module", "PyQt5.QtWebChannel",
    "--exclude-module", "PyQt5.QtWebSockets",
    "--exclude-module", "PyQt5.QtWinExtras",
    "--exclude-module", "PyQt5.QtXml",
    "--exclude-module", "PyQt5.QtXmlPatterns",
    MAIN,
]

mode = "单文件便携" if portable else "目录（启动快）"
print(f"[BUILD] BitForge — {mode} 模式...")
result = subprocess.run(cmd, cwd=SCRIPT_DIR)

if result.returncode == 0:
    if portable:
        exe = os.path.join(DIST, "BitForge.exe")
        print(f"\n[OK]  {mode} 打包完成!")
        print(f"     {exe}")
    else:
        src = os.path.join(DIST, "BitForge")
        dst = os.path.join(DIST, FOLDER_NAME)
        if os.path.exists(dst): shutil.rmtree(dst)
        os.rename(src, dst)
        exe = os.path.join(dst, "BitForge.exe")
        print(f"\n[OK]  {mode} 打包完成!")
        print(f"     {dst}\\")
        print(f"     ├─ BitForge.exe")
        print(f"     └─ ...(DLL 等依赖)")
    mb = os.path.getsize(exe) / 1024 / 1024
    print(f"     Size: {mb:.1f} MB")
else:
    print(f"\n[FAIL] exit code {result.returncode}")
    sys.exit(1)
