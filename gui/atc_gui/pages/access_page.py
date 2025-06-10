from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QCheckBox, QRadioButton, QComboBox, QPushButton
from PyQt6 import uic
import os

class AccessPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/access_page.ui')
        uic.loadUi(ui_path, self)

        # 예시: 콤보박스, 테이블, 체크박스, 라디오버튼, 버튼 등 위젯 연결
        self.combo_area: QComboBox = self.findChild(QComboBox, 'combo_area')
        self.btn_query: QPushButton = self.findChild(QPushButton, 'btn_query')
        self.table_status = self.findChild(type(self.table_status), 'table_status')
        self.chk_person: QCheckBox = self.findChild(QCheckBox, 'chk_person')
        self.chk_vehicle: QCheckBox = self.findChild(QCheckBox, 'chk_vehicle')
        self.radio_grade1: QRadioButton = self.findChild(QRadioButton, 'radio_grade1')
        self.radio_grade2: QRadioButton = self.findChild(QRadioButton, 'radio_grade2')
        self.radio_grade3: QRadioButton = self.findChild(QRadioButton, 'radio_grade3')
        self.combo_reason: QComboBox = self.findChild(QComboBox, 'combo_reason')
        self.btn_register: QPushButton = self.findChild(QPushButton, 'btn_register')

        # 시그널 연결 예시 (실제 로직은 필요에 따라 구현)
        # self.btn_query.clicked.connect(self.query_status)
        # self.btn_register.clicked.connect(self.register_condition)

    # def query_status(self):
    #     pass

    # def register_condition(self):
    #     pass 