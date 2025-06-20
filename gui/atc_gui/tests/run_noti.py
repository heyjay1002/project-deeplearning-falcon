import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QColor
from datetime import datetime
from tests.noti import NotificationDialog

# 더미 객체 클래스 정의 (실제 프로젝트의 DetectedObject 대신)
class DummyObject:
    def __init__(self):
        self.object_id = 101
        self.object_type = type('EnumValue', (), {'value': 'Bird'})()
        self.zone = type('EnumValue', (), {'value': 'RWY_A'})()
        self.timestamp = datetime.now()
        self.image_data = self.generate_dummy_image_bytes()

    def generate_dummy_image_bytes(self):
        # 빨간 사각형 이미지 생성
        image = QImage(200, 150, QImage.Format.Format_RGB32)
        image.fill(QColor(220, 20, 60))  # crimson

        buffer = image.bits().asstring(image.sizeInBytes())
        return bytes(buffer)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    test_data = DummyObject()
    dialog = NotificationDialog(notification_type='object', data=test_data)
    dialog.show()

    sys.exit(app.exec())
