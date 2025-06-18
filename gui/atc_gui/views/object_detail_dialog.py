from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
import sys
from typing import Optional, TYPE_CHECKING

# 타입 체킹용 import (런타임에서는 실행되지 않음)
if TYPE_CHECKING:
    from utils.interface import DetectedObject

# 상위 디렉토리를 파이썬 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from utils.interface import DetectedObject
    from utils.logger import logger
except ImportError as e:
    print(f"Import 오류: {e}")
    # 기본 로거 설정
    import logging
    logger = logging.getLogger(__name__)
    # DetectedObject를 임시로 정의 (실제 사용시에는 문제가 될 수 있음)
    DetectedObject = None

class ObjectDetailDialog(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/object_detail_dialog.ui')
        uic.loadUi(ui_path, self)
        
        # UI 요소 타입 힌팅
        self.detail_img: QLabel = self.findChild(QLabel, 'detail_img')
        self.detail_info: QLabel = self.findChild(QLabel, 'detail_info')
        self.btn_back: QPushButton = self.findChild(QPushButton, 'btn_back')
        
        # 이미지 라벨 설정
        self.detail_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_img.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        
        # 정보 라벨 설정
        self.detail_info.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ccc;
                padding: 10px;
                font-size: 12px;
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

    def update_object_info(self, obj) -> None:  # 타입 힌트 제거
        """객체 정보 업데이트"""
        try:
            # DetectedObject가 None인 경우 처리
            if DetectedObject is None:
                self.detail_info.setText("DetectedObject 클래스를 찾을 수 없습니다.")
                return
                
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
            
            # 정보 텍스트 업데이트
            info_text = f"""객체 상세 정보
ID: {getattr(obj, 'object_id', 'N/A')}
종류: {getattr(obj, 'object_type', {}).get('value', 'N/A') if hasattr(getattr(obj, 'object_type', {}), 'get') else getattr(getattr(obj, 'object_type', {}), 'value', 'N/A')}
위치: {getattr(obj, 'zone', {}).get('value', 'N/A') if hasattr(getattr(obj, 'zone', {}), 'get') else getattr(getattr(obj, 'zone', {}), 'value', 'N/A')}
발견 시각: {getattr(obj, 'timestamp', 'N/A')}"""
            
            if hasattr(obj, 'extra_info') and obj.extra_info:
                extra_info_value = getattr(obj.extra_info, 'value', obj.extra_info)
                info_text += f"\n추가 정보: {extra_info_value}"
            
            self.detail_info.setText(info_text)
            
        except Exception as e:
            if logger:
                logger.error(f"객체 정보 업데이트 실패: {e}")
            else:
                print(f"객체 정보 업데이트 실패: {e}")
            self.detail_info.setText("객체 정보를 표시할 수 없습니다.")
            self.detail_img.setText("이미지를 표시할 수 없습니다.")