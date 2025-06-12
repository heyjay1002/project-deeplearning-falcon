from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from models.detected_object import DetectedObject
from typing import Optional

class ObjectDetectionDialog(QDialog):
    def __init__(self, obj: DetectedObject, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("객체 감지 알림")
        self.setModal(True)
        
        # 레이아웃 설정
        layout: QVBoxLayout = QVBoxLayout()
        
        # 제목
        title: QLabel = QLabel("새로운 객체가 감지되었습니다")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 객체 정보
        info_text: str = f"객체 ID: {obj.object_id}\n"
        info_text += f"종류: {obj.object_type.value}\n"
        info_text += f"위치: {obj.zone.value}\n"
        info_text += f"발견 시각: {obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        info_label: QLabel = QLabel(info_text)
        info_label.setStyleSheet("font-size: 12pt;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # 확인 버튼
        ok_button: QPushButton = QPushButton("확인")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12pt;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(ok_button)
        
        self.setLayout(layout)
        
        # 다이얼로그 크기 설정
        self.setMinimumWidth(300)
        self.setMinimumHeight(200) 