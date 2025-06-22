import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from datetime import datetime
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import WindowClass  # main.py의 WindowClass 임포트
from utils.interface import DetectedObject, ObjectType, AirportZone

class CustomNotificationDialog(QDialog):
    def __init__(self, title, message, image_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)  # 최소 크기 확실히 지정

        layout = QVBoxLayout(self)

        # 메시지 텍스트
        label = QLabel(message)
        label.setMinimumHeight(60)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # 이미지가 있으면 추가
        if image_path:
            img_label = QLabel()
            pixmap = QPixmap(image_path)
            img_label.setPixmap(pixmap.scaledToWidth(500))  # 이미지 크기 조정
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(img_label)
        else:
            # 이미지가 없을 때도 공간 확보
            img_label = QLabel()
            img_label.setMinimumHeight(300)
            layout.addWidget(img_label)

        # 확인 버튼
        ok_btn = QPushButton("확인")
        ok_btn.setMinimumHeight(40)
        layout.addWidget(ok_btn)

        ok_btn.clicked.connect(self.accept)

def test_detection_dialog():
    # 테스트용 객체 생성
    test_obj = DetectedObject(
        object_id=1,
        object_type=ObjectType.BIRD,
        zone=AirportZone.RWY_A,
        x_coord=100,
        y_coord=200,
        timestamp=datetime.now()
    )

    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)

    # 메인 윈도우 생성
    window = WindowClass()
    window.show()

    # main.py의 알림 방식 사용
    window.show_notification_messagebox('object', test_obj)

    # 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    test_detection_dialog() 