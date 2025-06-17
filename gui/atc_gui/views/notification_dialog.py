from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor, QIcon
from utils.interface import DetectedObject, BirdRisk, RunwayRisk, ExtraInfo
from typing import Optional, Dict, Any
import base64
from io import BytesIO
from datetime import datetime

class NotificationDialog(QDialog):
    def __init__(self, notification_type: str, data: Dict[str, Any], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        
        # 알림 타입에 따른 제목 설정
        titles = {
            'object': "이상 객체 감지",
            'bird': "조류 충돌 위험 변화",
            'fallen_person': "쓰러진 인원 발생",
            'runway_a_risk': "활주로 A 위험 변화",
            'runway_b_risk': "활주로 B 위험 변화"
        }
        self.setWindowTitle("알림")
        
        # 메인 레이아웃 (수직)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(1)  # 위젯 간 간격 더 줄임
        main_layout.setContentsMargins(2, 1, 2, 2)  # 상단 여백 줄임
        
        # 제목 (상단 중앙)
        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 레이아웃 자체를 수직 중앙 정렬

        warning_icon = QLabel()
        warning_icon.setPixmap(QIcon.fromTheme("dialog-warning").pixmap(18, 18))
        warning_icon.setStyleSheet("margin: 0px; padding: 0px;")
        title_layout.addWidget(warning_icon)

        title = QLabel(titles.get(notification_type, "알림"))
        title.setStyleSheet("font-size: 12.5pt; font-weight: bold; margin: 0px; padding: 0px;")
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title.setFixedHeight(20)
        title_layout.addWidget(title)

        title_row_widget = QWidget()
        title_row_widget.setLayout(title_layout)
        title_row_widget.setFixedHeight(22)
        title_row_widget.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(title_row_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # 컨텐츠 레이아웃 (수평)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(2)  # 위젯 간 간격 최소화
        
        # 이미지 표시 (좌측)
        if notification_type == 'object':
            try:
                if isinstance(data, DetectedObject):
                    # 이미지 데이터 처리
                    if hasattr(data, 'image_data') and data.image_data:
                        if isinstance(data.image_data, str) and data.image_data.startswith('data:image'):
                            # Base64 이미지 데이터 디코딩
                            image_data = base64.b64decode(data.image_data.split(',')[1])
                        elif isinstance(data.image_data, bytes):
                            # 바이트 데이터 직접 사용
                            image_data = data.image_data
                        else:
                            raise ValueError("지원하지 않는 이미지 데이터 형식입니다.")
                        
                        image = QImage.fromData(image_data)
                    else:
                        # 이미지가 없는 경우 회색 pixmap 생성
                        image = QImage(120, 120, QImage.Format.Format_RGB32)
                        image.fill(QColor(200, 200, 200))
                else:
                    # DetectedObject가 아닌 경우 회색 pixmap 생성
                    image = QImage(120, 120, QImage.Format.Format_RGB32)
                    image.fill(QColor(200, 200, 200))
                
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    image_label = QLabel()
                    image_label.setPixmap(pixmap)
                    image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    image_label.setStyleSheet("background-color: #C8C8C8;")
                    image_label.setFixedSize(120, 120)  # 이미지 크기 조정
                    content_layout.addWidget(image_label)
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {str(e)}")
                # 오류 발생 시 회색 이미지 표시
                error_image = QImage(120, 120, QImage.Format.Format_RGB32)
                error_image.fill(QColor(200, 200, 200))
                error_pixmap = QPixmap.fromImage(error_image)
                error_label = QLabel()
                error_label.setPixmap(error_pixmap)
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet("background-color: #C8C8C8;")
                error_label.setFixedSize(120, 120)
                content_layout.addWidget(error_label)
        

        # 정보 표시 (우측)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)  # 위젯 간 간격 최소화
        
        # 알림 타입에 따른 정보 표시
        info_text = self._get_info_text(notification_type, data)
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 12pt;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 좌우 정렬은 유지하면서 상하 중앙 정렬 추가
        info_layout.addWidget(info_label)
        
        content_layout.addLayout(info_layout)
        main_layout.addLayout(content_layout)
        
        # 확인 버튼 (하단 중앙)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 0, 10, 0)  # 좌우 여백 추가
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
                min-width: 200px;  /* 버튼 최소 너비 증가 */
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(ok_button)
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
                   f"발견 시각: {data.timestamp}")
        
        elif notification_type == 'bird' and isinstance(data, BirdRisk):
            return f"조류 위험도: {data}"
        
        elif notification_type == 'fallen_person' and isinstance(data, DetectedObject):
            if data.extra_info == ExtraInfo.RESCUE:
                return (f"객체 ID: {data.object_id}\n"
                        f"쓰러진 인원 위치: {data.zone.value}")
        
        elif notification_type in ['runway_a_risk', 'runway_b_risk'] and isinstance(data, RunwayRisk):
            return f"활주로 {data.runway_id} 위험도: {data.enum.value}"
        
        return "알 수 없는 알림 유형입니다."