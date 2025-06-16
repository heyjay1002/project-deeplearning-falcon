from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor
from models.detected_object import DetectedObject
from typing import Optional, Dict, Any
import base64
from io import BytesIO

class NotificationDialog(QDialog):
    def __init__(self, notification_type: str, data: Dict[str, Any], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        
        # 알림 타입에 따른 제목 설정
        titles = {
            'object': "이상 객체 감지 알림",
            'bird': "조류 충돌 위험 알림",
            'fallen_person': "쓰러진 인원 알림"
        }
        self.setWindowTitle(titles.get(notification_type, "알림"))
        
        # 메인 레이아웃 (수직)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)  # 위젯 간 간격 최소화
        main_layout.setContentsMargins(2, 2, 2, 2)  # 여백 최소화
        
        # 제목 (상단 중앙)
        title = QLabel(titles.get(notification_type, "알림"))
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # 컨텐츠 레이아웃 (수평)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(2)  # 위젯 간 간격 최소화
        
        # 이미지 표시 (좌측)
        if notification_type == 'object':
            try:
                if isinstance(data, DetectedObject) and data.image_data:
                    # Base64 이미지 데이터 디코딩
                    image_data = base64.b64decode(data.image_data.split(',')[1])
                    image = QImage.fromData(image_data)
                else:
                    # 이미지가 없는 경우 회색 pixmap 생성
                    image = QImage(120, 120, QImage.Format.Format_RGB32)
                    image.fill(QColor(200, 200, 200))  # 회색으로 채우기
                
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    # 정사각형 크기로 조정
                    size = min(pixmap.width(), pixmap.height())
                    pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio)
                    image_label = QLabel()
                    image_label.setPixmap(pixmap)
                    image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    image_label.setStyleSheet("background-color: #C8C8C8;")
                    image_label.setFixedSize(120, 120)  # 이미지 크기 조정
                    content_layout.addWidget(image_label)
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {str(e)}")
        
        # 정보 표시 (우측)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)  # 위젯 간 간격 최소화
        
        # 알림 타입에 따른 정보 표시
        info_text = self._get_info_text(notification_type, data)
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 12pt;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(info_label)
        
        content_layout.addLayout(info_layout)
        main_layout.addLayout(content_layout)
        
        # 확인 버튼 (하단 중앙)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 2px 6px;
                font-size: 12pt;
                border-radius: 4px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 다이얼로그 크기 설정
        self.setFixedSize(280, 250)  # 크기를 280x250으로 고정
    
    def _get_info_text(self, notification_type: str, data: Dict[str, Any]) -> str:
        """알림 타입에 따른 정보 텍스트 생성"""
        if notification_type == 'object' and isinstance(data, DetectedObject):
            return (f"객체 ID: {data.object_id}\n"
                   f"종류: {data.object_type.value}\n"
                   f"위치: {data.zone.value}\n"
                   f"발견 시각: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        elif notification_type == 'bird':
            return (f"조류 종류: {data.get('species', '알 수 없음')}\n"
                   f"위치: {data.get('location', '알 수 없음')}\n"
                   f"발견 시각: {data.get('timestamp', '알 수 없음')}\n"
                   f"위험도: {data.get('risk_level', '알 수 없음')}")
        
        elif notification_type == 'fallen_person':
            return (f"위치: {data.get('location', '알 수 없음')}\n"
                   f"발견 시각: {data.get('timestamp', '알 수 없음')}\n"
                   f"상태: {data.get('condition', '알 수 없음')}\n"
                   f"응급 연락처: {data.get('emergency_contact', '알 수 없음')}")
        
        return "알 수 없는 알림 유형입니다." 