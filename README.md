# BitForge

<p align="center">
  <code style="font-size:48px;font-weight:bold;color:#6e40c9">🔧 BitForge</code>
</p>
<p align="center">
  <b>BitForge</b> — A programmer calculator for embedded engineers.<br>
  一款面向嵌入式工程师的程序员计算器，基于 PyQt5 + SiliconUI。
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#keyboard">Shortcuts</a> ·
  <a href="#build">Build</a> ·
  <a href="#license">License</a>
</p>

---

## Features / 功能

| Feature | Description |
|---------|-------------|
| 🧮 **Arithmetic** | `+` `−` `×` `/` `%` with integer division |
| 🔢 **Radix Switch** | HEX / DEC / OCT / BIN — input in any base |
| 📐 **Auto Bit-Width** | 8/16/32/64 bit auto-range, increases only, AC to reset |
| 🔟 **Multi-Radix Display** | All 4 bases shown simultaneously (2×2 layout) |
| 💡 **Bit Indicator** | Bit-level visualization with numbered positions |
| 🖱️ **Bit Click Toggle** | Click any bit to flip 0↔1 |
| ↔️ **64-bit Dual Row** | 64-bit splits into two 32-bit rows (63–32 / 31–0) |
| ± **Signed/Unsigned** | Toggle signed interpretation of DEC values |
| 🎨 **Light Theme** | Clean, bright interface — no theme switching |
| ⌨️ **Full Keyboard** | All operations accessible via keyboard |
| ⚡ **Fast Rendering** | QPixmap cache eliminates mouse-over lag |
| 🚀 **Quick Startup** | Delayed imports + immediate icon release |

---

## Screenshots / 截图

```
┌──────────────────────────────────────────┐
│ 🔧 BitForge  Programmer          v1.0.1 │
│ [HEX] [DEC] [OCT] [BIN]          [±] 32b│
│ ┌──────────────────────────────────────┐│
│ │                           0xDEADBEEF ││
│ └──────────────────────────────────────┘│
│ 63  62  ...         33  32             │
│ [ ][ ]...[ ][ ]          ← upper 32bit │
│ ─────────────────────────────────────── │
│ 31  30  ...          1   0             │
│ [ ][ ]...[ ][ ]          ← lower 32bit │
│                                        │
│ DEC  3735928559    HEX  0xDEADBEEF     │
│ OCT  0o33653337357 BIN  0b11011110...  │
│ ┌────┬────┬────┬────┬────┐             │
│ │ AC │ ⌫  │ %  │ /  │NOT │             │
│ │ 7  │ 8  │ 9  │ *  │AND │             │
│ │ 4  │ 5  │ 6  │ -  │ OR │             │
│ │ 1  │ 2  │ 3  │ +  │XOR │             │
│ │ 0  │ A  │ B  │ =  │ << │             │
│ │ C  │ D  │ E  │ F  │ >> │             │
│ └────┴────┴────┴────┴────┘             │
└──────────────────────────────────────────┘
```

---

## Quick Start / 快速开始

### Run from source (no install required)

```bash
python bitforge.py
```

Or double-click `run.bat` on Windows.

### Pre-built EXE

Download the latest release from [Releases](https://github.com/Hush-xv/BitForge/releases) — **no Python required**.

### Requirements

- Python 3.8+
- PyQt5 ≥ 5.15
- SiliconUI ≥ 1.0 (from [PyQt-SiliconUI](https://github.com/ChinaIceF/PyQt-SiliconUI))

```bash
pip install PyQt5 numpy typing_extensions
git clone https://github.com/ChinaIceF/PyQt-SiliconUI.git
cd PyQt-SiliconUI && python setup.py install
```

---

## Keyboard Shortcuts / 键盘快捷键

| Key | Action |
|-----|--------|
| `0`–`9` | Digit input |
| `A`–`F` | Hex digits (HEX mode only) |
| `+` `-` `*` `/` `%` | Arithmetic operators |
| `&` `\|` `^` `~` | Bitwise AND / OR / XOR / NOT |
| `<` `>` | Left shift / Right shift |
| `Enter` / `=` | Evaluate |
| `Backspace` | Delete last digit |
| `Esc` / `Delete` | Clear all (AC) |

---

## Build / 打包

```bash
pip install pyinstaller

# Directory mode (fast startup) — output: dist/BitForge/
python build.py

# Single-file mode (portable) — output: dist/BitForge.exe
python build.py --portable
```

---

## Project Structure / 项目结构

```
BitForge/
├── bitforge.py       # Main application (~540 lines)
├── build.py          # PyInstaller packaging script
├── bitforge.ico      # Application icon (256×256)
├── run.bat           # Quick-launch script
├── README.md
└── dist/
    └── BitForge/     # Standalone distribution
        └── BitForge.exe
```

---

## Tech Stack / 技术栈

| Layer | Technology |
|-------|-----------|
| **UI Framework** | [PyQt5](https://pypi.org/project/PyQt5/) |
| **Widget Library** | [PyQt-SiliconUI](https://github.com/ChinaIceF/PyQt-SiliconUI) |
| **Packaging** | PyInstaller (onedir / onefile) |
| **Theme** | Hardcoded light theme (30+ color tokens) |

---

## License / 许可证

BitForge is licensed under the **GPLv3** License, inherited from PyQt-SiliconUI.

```
Copyright (C) 2025 Hush-xv

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License.
```

---

## Acknowledgments / 致谢

- [ChinaIceF/PyQt-SiliconUI](https://github.com/ChinaIceF/PyQt-SiliconUI) — The elegant PyQt5 UI framework
- Built via [vibe coding](https://github.com/Hush-xv/BitForge) — conversational AI-assisted development
