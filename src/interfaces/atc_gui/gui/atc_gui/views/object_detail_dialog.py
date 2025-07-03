from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from typing import Optional
from utils.logger import logger
from utils.interface import DetectedObject

class ObjectDetailDialog(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/object_detail_dialog.ui')
        uic.loadUi(ui_path, self)
        
        # UI 요소 타입 힌팅
        self.title_label: QLabel = self.findChild(QLabel, 'title_label')
        self.detail_img: QLabel = self.findChild(QLabel, 'detail_img')
        self.event_type_label: QLabel = self.findChild(QLabel, 'event_type_label')
        self.detail_info: QLabel = self.findChild(QLabel, 'detail_info')
        self.btn_back: QPushButton = self.findChild(QPushButton, 'btn_back')
        
        # 제목 라벨 설정
        self.title_label.setText("객체 상세 정보")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #111;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # 이미지 라벨 설정
        self.detail_img.setFixedSize(300, 200)
        self.detail_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_img.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        
        # 이벤트 타입 라벨 설정
        self.event_type_label.setStyleSheet("""
            QLabel {
                background-color: #e8f4fd;
                border: 1px solid #4a90e2;
                padding: 2px 8px;
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                min-width: 80px;
                max-width: 160px;
                min-height: 24px;
                max-height: 32px;
                qproperty-alignment: 'AlignCenter';
                border-radius: 6px;
            }
        """)
        
        # 정보 라벨 설정
        self.detail_info.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ccc;
                padding: 10px;
                font-size: 16px;
            }
        """)
        
        # 뒤로가기 버튼 설정
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)

    def update_object_info(self, obj: DetectedObject) -> None:
        try:
            if not obj:
                logger.error("객체 정보가 없습니다.")
                return
            
            self._update_image(obj)
            self._update_event_type(obj)
            self._update_info(obj)
            
        except Exception as e:
            logger.error(f"객체 정보 업데이트 실패: {e}")
            
    def _update_image(self, obj: DetectedObject):
        # 이미지 업데이트
        if hasattr(obj, 'image_data') and obj.image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(obj.image_data)
            scaled_pixmap = pixmap.scaled(
                self.detail_img.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.detail_img.setPixmap(scaled_pixmap)
        else:
            self.detail_img.setText("이미지 없음")
            self.detail_img.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    color: #666;
                    font-size: 14px;
                }
            """)      

    def _update_event_type(self, obj: DetectedObject):
        # 이벤트 타입 업데이트
        event_type_value = getattr(getattr(obj, 'event_type', None), 'value', 'N/A')
        self.event_type_label.setText(str(event_type_value) if event_type_value else "-")
            
    def _update_info(self, obj: DetectedObject):
        # 정보 텍스트 업데이트
        info_text = f"""ID: {getattr(obj, 'object_id', 'N/A')}
종류: {getattr(getattr(obj, 'object_type', None), 'value', 'N/A')}
위치: {getattr(getattr(obj, 'area', None), 'value', 'N/A')}
발견 시각: {getattr(obj, 'timestamp', 'N/A')}"""
            
        if hasattr(obj, 'state_info') and obj.state_info:
            state_info_value = obj.state_info
            info_text += f"\n위험도: {state_info_value}"
        
        self.detail_info.setText(info_text)            

