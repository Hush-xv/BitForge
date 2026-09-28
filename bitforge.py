"""BitForge — Programmer Calculator (Fast Edition)

基于 PyQt5 + SiliconUI · 亮/暗双主题 · 表达式模式 · 位工具

入口薄壳: 实现已拆分至 bitforge/ 包, 本文件保留 `python bitforge.py` 启动方式。
导入接口由 bitforge/__init__.py 兼容层提供, 原有 `from bitforge import X` 不受影响。
运行: python bitforge.py  (或 python -m bitforge)
调试: 设 BITFORGE_DEBUG=1 输出关键路径日志
"""
from bitforge.app import main

if __name__ == "__main__":
    main()
