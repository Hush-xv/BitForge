"""
BitForge — PyInstaller 打包脚本
用法:
    python build.py              # 目录模式 BitForge/（启动快，文件夹分发）
    python build.py --portable   # 单 exe BitForge.exe（方便分发，启动稍慢）
"""
import os, shutil, subprocess, sys, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(SCRIPT_DIR, "bitforge.py")
ICON = os.path.join(SCRIPT_DIR, "bitforge.ico")
DIST = os.path.join(SCRIPT_DIR, "dist")
WORK = os.path.join(SCRIPT_DIR, "build_bitforge")

def rm_tree(path, retries=5):
    # dist 在桌面目录下, OneDrive/索引器会短暂锁住新写入的文件, 需重试
    for i in range(retries):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            time.sleep(1 + i)
    shutil.rmtree(path, ignore_errors=True)

def rm_file(path, retries=5):
    for i in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(1 + i)

portable = "--portable" in sys.argv
FOLDER_NAME = "BitForge"

for d in [DIST, WORK]:
    if os.path.exists(d): rm_tree(d)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile" if portable else "--onedir",
    "--windowed",
    "--name", "BitForge",
    "--distpath", DIST,
    "--workpath", WORK,
    f"--icon={ICON}",
    # siui 携带 SVG 图标资源, 必须整体收集
    "--collect-all", "siui",
    # 注意: 不加 --collect-all PyQt5。PyInstaller 钩子按 import 收集
    # QtCore/QtGui/QtWidgets/QtSvg。numpy 被 siui 5 处硬导入, 自动包含。
    #
    # 下面这些 exclude 仍然必需: siui/components/widgets/container.py
    # 有 `from PyQt5.Qt import QColor`, 全域模块 PyQt5.Qt 会把所有
    # PyQt5 子模块加进 hiddenimports; exclude 优先级更高, 可拦掉
    # 本应用用不到的大模块 (Qml/Quick/Multimedia/Bluetooth 等)。
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

# ----- onedir 后处理: 删除用不到的 Qt 运行时 (约省 45MB) -----
# QtWidgets 应用只需 Core/Gui/Widgets/Svg。PyInstaller 的二进制依赖
# 扫描会多带 Qml/Quick/Network 链和软件 OpenGL 回退, 这里显式删掉。
QT_DROP_DLLS = [
    "Qt5Qml.dll", "Qt5QmlModels.dll", "Qt5Quick.dll",
    "Qt5WebSockets.dll", "Qt5DBus.dll", "Qt5Network.dll",
    "opengl32sw.dll", "d3dcompiler_47.dll",
    "libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll",
]

def cleanup_qt(root):
    bin_dir = os.path.join(root, "_internal", "PyQt5", "Qt5", "bin")
    for name in QT_DROP_DLLS:
        p = os.path.join(bin_dir, name)
        if os.path.exists(p): rm_file(p)
    # TLS 插件依赖 Qt5Network, 一并移除
    tls = os.path.join(root, "_internal", "PyQt5", "Qt5", "plugins", "tls")
    if os.path.exists(tls): rm_tree(tls)
    # 翻译只留 qtbase (对话框按钮等标准文案)
    tr = os.path.join(root, "_internal", "PyQt5", "Qt5", "translations")
    if os.path.exists(tr):
        for f in os.listdir(tr):
            if not f.startswith("qtbase"):
                fp = os.path.join(tr, f)
                rm_tree(fp) if os.path.isdir(fp) else rm_file(fp)

if result.returncode == 0 and not portable:
    cleanup_qt(os.path.join(DIST, "BitForge"))

if result.returncode == 0:
    if portable:
        exe = os.path.join(DIST, "BitForge.exe")
        print(f"\n[OK]  {mode} 打包完成!")
        print(f"     {exe}")
    else:
        src = os.path.join(DIST, "BitForge")
        dst = os.path.join(DIST, FOLDER_NAME)
        if src != dst:
            if os.path.exists(dst): rm_tree(dst)
            os.rename(src, dst)
            exe = os.path.join(dst, "BitForge.exe")
        else:
            exe = os.path.join(src, "BitForge.exe")
        print(f"\n[OK]  {mode} 打包完成!")
        print(f"     {dst}\\")
        print(f"     ├─ BitForge.exe")
        print(f"     └─ ...(DLL 等依赖)")
    mb = os.path.getsize(exe) / 1024 / 1024
    print(f"     Size: {mb:.1f} MB")
else:
    print(f"\n[FAIL] exit code {result.returncode}")
    sys.exit(1)
