from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from utils.logger import logger

class NotificationDialog(QDialog):
    """알림 다이얼로그"""

    def __init__(self, notification_type: str, data: any, parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.data = data

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        self.adjust_position()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #AAAAAA;
            }
            QLabel {
                color: #222222;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 제목
        title_label = QLabel(self.get_title())
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # 본문: 이미지 + 정보
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # 이미지
        if hasattr(self.data, 'image_data') and self.data.image_data:
            try:
                image = QImage.fromData(self.data.image_data)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    image_label = QLabel()
                    image_label.setPixmap(pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio))
                    content_layout.addWidget(image_label)
            except Exception as e:
                logger.error(f"이미지 처리 오류: {str(e)}")

        # 정보
        info_layout = QFormLayout()
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        if self.notification_type == 'object':
            info_layout.addRow("객체 ID:", QLabel(str(self.data.object_id)))
            info_layout.addRow("종류:", QLabel(str(self.data.object_type.value)))
            info_layout.addRow("위치:", QLabel(str(self.data.zone.value)))
            if hasattr(self.data, 'timestamp'):
                info_layout.addRow("발견 시각:", QLabel(str(self.data.timestamp)))
        else:
            info_layout.addRow("정보:", QLabel(str(self.data)))

        content_layout.addLayout(info_layout)
        main_layout.addLayout(content_layout)

        # 버튼 (중앙 정렬)
        button = QPushButton("확인")
        button.clicked.connect(self.close)
        main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def get_title(self) -> str:
        return {
            'object': '이상 객체 감지',
            'bird': '조류 충돌 위험 변화',
            'runway_a_risk': '활주로 A 위험도 변화',
            'runway_b_risk': '활주로 B 위험도 변화'
        }.get(self.notification_type, '알림')

    def adjust_position(self):
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.right() - self.width() - 20
            y = parent_rect.bottom() - self.height() - 20
            screen_geometry = self.parent().screen().geometry()
            x = min(x, screen_geometry.right() - self.width() - 20)
            y = min(y, screen_geometry.bottom() - self.height() - 20)
            self.move(x, y)

    def mousePressEvent(self, event):
        self.close()

    def showEvent(self, event):
        super().showEvent(event)
        self.adjust_position()
