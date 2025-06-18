from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
import cv2
import numpy as np
from utils.logger import logger

class NotificationDialog(QDialog):
    """알림 다이얼로그"""
    
    def __init__(self, notification_type: str, data: any, parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.data = data
        
        # 창 설정
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 레이아웃 설정
        self.setup_ui()
        
        # 위치 조정
        self.adjust_position()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 제목 설정
        title = self.get_title()
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        # 내용 설정
        content = self.get_content()
        content_label = QLabel(content)
        content_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                padding: 5px;
            }
        """)
        
        # 확인 버튼
        close_button = QPushButton("확인")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        close_button.clicked.connect(self.close)
        
        # 레이아웃에 위젯 추가
        layout.addWidget(title_label)
        layout.addWidget(content_label)
        
        # 이미지가 있는 경우 추가
        if hasattr(self.data, 'image_data') and self.data.image_data:
            try:
                # 바이트 데이터를 QImage로 변환
                image = QImage.fromData(self.data.image_data)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    image_label = QLabel()
                    image_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
                    layout.addWidget(image_label)
            except Exception as e:
                logger.error(f"이미지 처리 중 오류 발생: {str(e)}")
        
        layout.addWidget(close_button)
        
        # 스타일 설정
        self.setStyleSheet("""
            QDialog {
                background-color: #2C3E50;
                border-radius: 10px;
                border: 1px solid #34495E;
            }
        """)
        
    def get_title(self) -> str:
        """알림 제목 반환"""
        titles = {
            'object': '이상 객체 감지',
            'bird': '조류 충돌 위험 변화',
            'runway_a_risk': '활주로 A 위험도 변화',
            'runway_b_risk': '활주로 B 위험도 변화'
        }
        return titles.get(self.notification_type, '알림')
        
    def get_content(self) -> str:
        """알림 내용 반환"""
        if self.notification_type == 'object':
            return f"객체 ID: {self.data.object_id}\n종류: {self.data.object_type.value}\n위치: {self.data.zone.value}"
        elif self.notification_type == 'bird':
            return f"조류 위험도: {self.data.bird_risk_level}"
        elif self.notification_type in ['runway_a_risk', 'runway_b_risk']:
            return f"활주로 {self.data.runway_id} 위험도: {self.data.runway_risk_level}"
        return str(self.data)
        
    def adjust_position(self):
        """다이얼로그 위치 조정"""
        if self.parent():
            # 부모 위젯의 우측 하단 위치 계산
            parent_rect = self.parent().geometry()
            x = parent_rect.right() - self.width() - 20  # 우측에서 20px 여백
            y = parent_rect.bottom() - self.height() - 20  # 하단에서 20px 여백
            
            # 화면 밖으로 나가지 않도록 조정
            screen_geometry = self.parent().screen().geometry()
            x = min(x, screen_geometry.right() - self.width() - 20)
            y = min(y, screen_geometry.bottom() - self.height() - 20)
            
            self.move(x, y)
            
    def mousePressEvent(self, event):
        """마우스 클릭 시 다이얼로그 닫기"""
        self.close()
        
    def showEvent(self, event):
        """다이얼로그 표시 시 위치 조정"""
        super().showEvent(event)
        self.adjust_position()