from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
import os

class ObjectDetailDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/object_detail_dialog.ui')
        uic.loadUi(ui_path, self)
        # self.detail_img, self.detail_info, self.btn_back에 접근 가능 