"""BitForge 应用入口。"""
import sys

from PyQt5.QtWidgets import QApplication

from .main_window import BitForge
from .widgets import make_app_icon


def main():
    app=QApplication(sys.argv); app.setApplicationName("BitForge")
    app.setWindowIcon(make_app_icon())
    w=BitForge(); w.show()
    # 立即释放图标包内存 (~50MB, 5410 个 SVG)
    from siui.core import SiGlobal
    if hasattr(SiGlobal.siui,'iconpack') and hasattr(SiGlobal.siui.iconpack,'clear'):
        SiGlobal.siui.iconpack.clear()
    sys.exit(app.exec_())
if __name__=="__main__": main()
