from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6 import uic
import os
from typing import Optional

class ObjectDetailDialog(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/object_detail_dialog.ui')
        uic.loadUi(ui_path, self)
        
        # UI 요소 타입 힌팅
        self.detail_img: QLabel = self.findChild(QLabel, 'detail_img')
        self.detail_info: QLabel = self.findChild(QLabel, 'detail_info')
        self.btn_back: QPushButton = self.findChild(QPushButton, 'btn_back')
        # self.detail_img, self.detail_info, self.btn_back에 접근 가능 