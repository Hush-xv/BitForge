# BitForge

<p align="center">
  <img src="https://raw.githubusercontent.com/Hush-xv/BitForge/main/concept.html" width="60" alt="BitForge Logo" />
</p>
<p align="center">
  <b>BitForge</b> — A sleek programmer calculator built with PyQt5 + SiliconUI.<br>
  一款精致的程序员计算器，基于 PyQt5 + SiliconUI 构建。
</p>
<p align="center">
  <a href="#features">Features</a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#installation">Install</a> ·
  <a href="#keyboard">Shortcuts</a> ·
  <a href="#build">Build</a> ·
  <a href="#license">License</a>
</p>

---

## Features / 功能

| Feature | Description |
|---------|-------------|
| 🧮 **Arithmetic** | `+` `−` `×` `/` `%` with integer division |
| 🔢 **Radix Switch** | HEX / DEC / OCT / BIN — digit keys auto-adapt |
| 📏 **Bit Width** | 8 / 16 / 32 / 64-bit with automatic overflow clamping |
| ⚡ **Bitwise Ops** | AND · OR · XOR · NOT · `<<` · `>>` |
| 👁️ **Live Preview** | All four radices displayed simultaneously |
| 💡 **Bit Indicator** | Binary bits grouped by byte, with purple radial glow |
| 🎨 **Dual Theme** | Dark / Light theme with data-driven color system |
| ⚙️ **Settings** | QMenu-based settings panel (theme toggle + version info) |
| ⌨️ **Full Keyboard** | All operations accessible via keyboard |
| 🎬 **Animations** | SiliconUI hover highlight + press-scale rebound |
| 🏷️ **Icons** | Fluent UI SVG icons (5,400+ available) |

---

## Screenshots / 截图

> *Run `python bitforge.py` to see it live, or open `concept.html` in your browser for a static preview.*

### Dark Theme / 暗色主题

```
┌──────────────────────────────────────┐
│ 🧮 BitForge  Programmer      ⚙ v1.2 │
│ ┌──────────────────────────────────┐ │
│ │  0x                           0  │ │
│ │  11111111 11111111 00000000 ...  │ │
│ └──────────────────────────────────┘ │
│  DEC  0  │ HEX  0x0 │ OCT  0 │ BIN │
│ ┌────┬────┬────┬────┬────┐         │
│ │ AC │ ⌫  │ %  │ ÷  │NOT │         │
│ │ 7  │ 8  │ 9  │ ×  │AND │         │
│ │ 4  │ 5  │ 6  │ −  │ OR │         │
│ │ 1  │ 2  │ 3  │ +  │XOR │         │
│ │ 0  │ A  │ B  │ =  │ << │         │
│ │ C  │ D  │ E  │ F  │ >> │         │
│ └────┴────┴────┴────┴────┘         │
└──────────────────────────────────────┘
```

---

## Installation / 安装

### Option 1: Pre-built EXE (Windows)

Download `BitForge.exe` from [Releases](https://github.com/Hush-xv/BitForge/releases) and run — **no Python required**.

### Option 2: Run from source

```bash
# 1. Install PyQt5
pip install PyQt5 numpy typing_extensions

# 2. Install SiliconUI framework
git clone https://github.com/ChinaIceF/PyQt-SiliconUI.git
cd PyQt-SiliconUI
python setup.py install

# 3. Run BitForge
cd examples/BitForge
python bitforge.py
```

**Requirements:**
- Python 3.8+
- PyQt5 ≥ 5.15
- SiliconUI ≥ 1.0
- numpy
- typing_extensions

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

## Build from Source / 从源码构建

```bash
# Generate standalone EXE
python build.py
```

This uses **PyInstaller** to produce a single `dist/BitForge.exe` (~76 MB, self-contained).

```bash
pip install pyinstaller   # one-time setup
python build.py           # produces dist/BitForge.exe
```

---

## Project Structure / 项目结构

```
BitForge/
├── bitforge.py          # Main application (~500 lines)
├── build.py             # PyInstaller packaging script
├── concept.html          # Static design mockup (SiliconUI style)
├── dist/
│   └── BitForge.exe      # Standalone executable
└── README.md
```

---

## Tech Stack / 技术栈

| Layer | Technology |
|-------|-----------|
| **UI Framework** | [PyQt5](https://pypi.org/project/PyQt5/) |
| **Component Library** | [PyQt-SiliconUI](https://github.com/ChinaIceF/PyQt-SiliconUI) |
| **Icons** | Fluent UI System Icons (5,400+ SVG) |
| **Animation** | `SiExpAnimationRefactor` — exponential easing |
| **Packaging** | PyInstaller (single-file EXE) |
| **Theme System** | Data-driven `AppTheme` dict (30+ color tokens) |

---

## License / 许可证

BitForge is licensed under the **GPLv3** License, inherited from PyQt-SiliconUI.

```
Copyright (C) 2025 Hush-xv

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
```

---

## Acknowledgments / 致谢

- [ChinaIceF/PyQt-SiliconUI](https://github.com/ChinaIceF/PyQt-SiliconUI) — The elegant PyQt5 UI framework powering BitForge's visuals
- [Microsoft Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) — 5,400+ SVG icons used throughout the interface
