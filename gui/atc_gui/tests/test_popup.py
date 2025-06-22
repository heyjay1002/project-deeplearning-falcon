from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout, QFormLayout, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from datetime import datetime
import sys

class ObjectPopup(QDialog):
    def __init__(self, image_path, object_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("이상 객체 감지")

        layout = QVBoxLayout()

        # 이미지 표시
        image_label = QLabel()
        pixmap = QPixmap(image_path)
        image_label.setPixmap(pixmap.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(image_label)

        # 객체 정보 표시
        form_layout = QFormLayout()
        form_layout.addRow("객체 ID:", QLabel(str(object_info["id"])))
        form_layout.addRow("객체 종류:", QLabel(str(object_info["type"])))
        form_layout.addRow("위치:", QLabel(str(object_info["zone"])))
        form_layout.addRow("발견 시각:", QLabel(str(object_info["timestamp"])))
        layout.addLayout(form_layout)

        # 확인 버튼
        close_button = QPushButton("확인")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setModal(True)  # 필요 시

# 테스트 코드 (단독 실행용)
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    obj_info = {
        "id": 42,
        "type": "Bird",
        "zone": "RWY_A",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    dlg = ObjectPopup("sample.jpg", obj_info)
    dlg.exec()
