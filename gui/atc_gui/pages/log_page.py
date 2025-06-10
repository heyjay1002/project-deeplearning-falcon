from PyQt6.QtWidgets import QWidget, QComboBox, QLabel, QDateEdit, QPushButton, QTableWidget, QTableWidgetItem
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QDate
import os

class LogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/log_page.ui')
        uic.loadUi(ui_path, self)

        self.combo_log: QComboBox = self.findChild(QComboBox, 'combo_log')
        self.combo_type: QComboBox = self.findChild(QComboBox, 'combo_type')
        self.label_type: QLabel = self.findChild(QLabel, 'label_type')
        self.btn_show_img: QPushButton = self.findChild(QPushButton, 'btn_show_img')
        self.btn_search: QPushButton = self.findChild(QPushButton, 'btn_search')
        self.start_date: QDateEdit = self.findChild(QDateEdit, 'start_date')
        self.end_date: QDateEdit = self.findChild(QDateEdit, 'end_date')
        self.table_result: QTableWidget = self.findChild(QTableWidget, 'table_result')

        self.combo_log.currentIndexChanged.connect(self.update_mode)
        self.btn_search.clicked.connect(self.search_log)
        self.update_mode(0)

    def update_mode(self, idx):
        # 이상 객체 감지 이력
        if idx == 0:
            self.combo_type.show()
            self.label_type.show()
            self.btn_show_img.show()
            self.table_result.setColumnCount(5)
            self.table_result.setHorizontalHeaderLabels(['일시', '구역', '종류', '상태', '비고'])
        # 출입 조건 위반 이력
        else:
            self.combo_type.hide()
            self.label_type.hide()
            self.btn_show_img.hide()
            self.table_result.setColumnCount(4)
            self.table_result.setHorizontalHeaderLabels(['일시', '구역', '상태', '비고'])
        self.table_result.setRowCount(0)

    def search_log(self):
        idx = self.combo_log.currentIndex()
        self.table_result.setRowCount(0)
        self.table_result.setSelectionBehavior(self.table_result.SelectionBehavior.SelectRows)
        # 더미 데이터 예시
        if idx == 0:
            # 이상 객체 감지 이력
            dummy = [
                ['2024-06-01 12:00', 'TWY A', '조류', '감지', '사진 있음'],
                ['2024-06-02 13:00', 'TWY B', '기타', '감지', '사진 없음'],
            ]
            self.table_result.setRowCount(len(dummy))
            for row, data in enumerate(dummy):
                for col, value in enumerate(data):
                    self.table_result.setItem(row, col, QTableWidgetItem(value))
        else:
            # 출입 조건 위반 이력
            dummy = [
                ['2024-06-01 09:00', 'TWY A', '위반', '경고'],
                ['2024-06-03 10:30', 'TWY B', '위반', '조치 완료'],
            ]
            self.table_result.setRowCount(len(dummy))
            for row, data in enumerate(dummy):
                for col, value in enumerate(data):
                    self.table_result.setItem(row, col, QTableWidgetItem(value))
        