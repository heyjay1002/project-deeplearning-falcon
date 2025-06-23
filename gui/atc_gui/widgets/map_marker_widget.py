from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal, QEasingCurve, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from utils.logger import logger
from config.constants import ObjectType
from utils.interface import DetectedObject

class MarkerState(Enum):
    """마커 상태"""
    NORMAL = "normal"    # 일반적인 객체 감지 상태
    WARNING = "warning"  # 구조가 필요한 사람 감지 상태
    SELECTED = "selected"  # 사용자가 선택한 상태

@dataclass
class MarkerData:
    """마커 데이터"""
    object_id: int
    x: float
    y: float
    object_type: str
    zone: str
    is_selected: bool = False
    size: int = 50
    icon_path: Optional[str] = None
    state: str = 'NORMAL'  # NORMAL, WARNING, SELECTED

class DynamicMarker(QLabel):
    """동적 마커 위젯"""
    clicked = pyqtSignal(int)   # object_id 전달
    
    def __init__(self, data: MarkerData, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_animating = False
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._animation_finished)
        
        # 마커 설정
        self.setup_marker()
        
    def setup_marker(self):
        """마커 초기 설정"""
        # 크기 설정
        self.setFixedSize(self.data.size, self.data.size)
        
        # 마커 이미지 생성
        self.update_appearance()
        
        # 클릭 가능하도록 설정
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def update_appearance(self):
        """마커 외관 업데이트"""
        # 기본 아이콘 또는 커스텀 아이콘 사용
        if self.data.icon_path and os.path.exists(self.data.icon_path):
            pixmap = QPixmap(self.data.icon_path)
        else:
            # 기본 마커 생성
            pixmap = self.create_default_marker()
            
        # 상태에 따른 효과 추가
        if self.data.state != 'NORMAL':
            pixmap = self.add_state_effect(pixmap)
            
        # 스케일링
        scaled_pixmap = pixmap.scaled(
            self.data.size, self.data.size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)
        
    def create_default_marker(self) -> QPixmap:
        """기본 마커 생성"""
        size = self.data.size
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 객체 타입별 아이콘 경로 매핑 (ObjectType Enum의 value 사용)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_paths = {
            ObjectType.BIRD.value: os.path.join(base_path, 'resources/images/bird.png'),
            ObjectType.FOD.value: os.path.join(base_path, 'resources/images/fod.png'),
            ObjectType.PERSON.value: os.path.join(base_path, 'resources/images/person.png'),
            ObjectType.ANIMAL.value: os.path.join(base_path, 'resources/images/animal.png'),
            ObjectType.AIRPLANE.value: os.path.join(base_path, 'resources/images/airplane.png'),
            ObjectType.VEHICLE.value: os.path.join(base_path, 'resources/images/vehicle.png'),
            ObjectType.WORK_PERSON.value: os.path.join(base_path, 'resources/images/worker.png'),
            ObjectType.WORK_VEHICLE.value: os.path.join(base_path, 'resources/images/vehicle_work.png')
        }
        # Enum이 들어오면 value, 아니면 그대로
        obj_type_key = self.data.object_type.value if hasattr(self.data.object_type, 'value') else str(self.data.object_type)
        icon_path = icon_paths.get(obj_type_key)
        logger.debug(f"마커 아이콘 로드 시도: base_path={base_path}, object_type={obj_type_key}, icon_path={icon_path}")
        logger.debug(f"사용 가능한 icon_paths 키들: {list(icon_paths.keys())}")
        
        if icon_path and os.path.exists(icon_path):
            logger.debug(f"아이콘 파일 존재 확인: {icon_path}")
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
                logger.debug(f"아이콘 로드 성공: {icon_path}")
                # 흰색 배경 그리기
                painter.setBrush(QBrush(QColor("white")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(2, 2, size - 4, size - 4, 8, 8)
                
                # 아이콘 크기 조정
                scaled_icon = icon_pixmap.scaled(
                    size - 4, size - 4,  # 마진 2px
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # 아이콘 중앙에 그리기
                x = (size - scaled_icon.width()) // 2
                y = (size - scaled_icon.height()) // 2
                painter.drawPixmap(x, y, scaled_icon)
                
                # 상태에 따른 테두리 추가
                if self.data.state == 'WARNING':
                    painter.setPen(QPen(QColor("#FFA500"), 2))  # 주황색
                elif self.data.state == 'SELECTED':
                    painter.setPen(QPen(QColor("#FFD700"), 2))  # 금색
                else:
                    painter.setPen(QPen(QColor("#FFFFFF"), 2))  # 흰색
                    
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(2, 2, size - 4, size - 4, 8, 8)
                
                painter.end()
                return pixmap
            else:
                logger.warning(f"아이콘 로드 실패 (null): {icon_path}")
        else:
            logger.debug(f"아이콘 파일을 찾을 수 없음: {icon_path}")
        
        # 아이콘 로드 실패 시 기본 마커 생성
        logger.debug("기본 파란색 마커 생성")
        default_color = QColor("#4A90E2")  # 기본 파란색
        
        # 기본 마커 그리기
        painter.setBrush(QBrush(default_color))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        
        # 둥근 모서리 사각형 그리기
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 8, 8)
        
        painter.end()
        return pixmap
        
    def add_state_effect(self, pixmap: QPixmap) -> QPixmap:
        """상태 효과 추가"""
        if self.data.state == 'SELECTED':
            # 강조 효과 생성
            enhanced = QPixmap(pixmap.size())
            enhanced.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(enhanced)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 원본 마커 그리기
            painter.drawPixmap(0, 0, pixmap)
            
            # 선택된 마커 테두리 강조
            painter.setPen(QPen(QColor("#FFD700"), 3))  # 금색, 3px 두께
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, pixmap.width() - 2, pixmap.height() - 2, 8, 8)
            
            painter.end()
            return enhanced
            
        elif self.data.state == 'WARNING':
            # 경고/위험 상태는 깜빡임 효과
            enhanced = QPixmap(pixmap.size())
            enhanced.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(enhanced)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 원본 마커 그리기
            painter.drawPixmap(0, 0, pixmap)
            
            # 깜빡임 효과를 위한 반투명 오버레이
            if hasattr(self, 'blink_visible') and self.blink_visible:
                overlay_color = QColor("#FFA500")
                overlay_color.setAlpha(128)  # 50% 투명도
                painter.setBrush(QBrush(overlay_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 8, 8)
            
            painter.end()
            return enhanced
            
        return pixmap
    
    def animate_to_position(self, x: int, y: int):
        """위치로 애니메이션"""
        self.is_animating = True
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(x, y))
        self.animation.setDuration(300)
        self.animation.start()
        
    def _animation_finished(self):
        """애니메이션 완료 처리"""
        self.is_animating = False
        
    def start_blinking(self):
        """깜빡임 효과 시작"""
        if not hasattr(self, 'blink_timer'):
            self.blink_timer = QTimer()
            self.blink_timer.timeout.connect(self.toggle_visibility)
            self.blink_visible = True
            
        self.blink_timer.start(500)  # 0.5초 간격
        
    def stop_blinking(self):
        """깜빡임 효과 중지"""
        if hasattr(self, 'blink_timer'):
            self.blink_timer.stop()
            self.setVisible(True)
    
    def toggle_visibility(self):
        """가시성 토글 (깜빡임 용)"""
        self.blink_visible = not self.blink_visible
        self.update_appearance()  # 마커 외관 업데이트
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data.object_id)
        super().mousePressEvent(event)

class MapMarkerWidget(QWidget):
    """지도 마커 위젯"""
    marker_clicked = pyqtSignal(int)  # object_id 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.markers: Dict[int, DynamicMarker] = {}
        self.marker_labels: Dict[int, QLabel] = {}  # 추가
        self.selected_marker_id: Optional[int] = None
        self.set_map_size(960, 720)  # 기본 지도 크기
        
        # 지도 이미지를 표시할 레이블 생성
        self.label_map = QLabel(self)
        self.label_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label_map)
        
        # 지도 이미지 설정
        self.set_map_image()
        
    def set_map_size(self, width: int, height: int):
        """지도 크기 설정"""
        self.map_width = width
        self.map_height = height
        self.update_marker_positions()
        
    def set_map_image(self):
        """지도 이미지 설정"""
        # 지도 이미지 경로 설정
        self.map_path = os.path.join(os.path.dirname(__file__), '../resources/images/map_crop.png')
        self.map_pixmap = QPixmap()
        
        if os.path.exists(self.map_path):
            if self.map_pixmap.load(self.map_path):
                logger.info(f"지도 이미지 로드 성공: {self.map_path}")
            else:
                logger.warning(f"지도 이미지 로드 실패: {self.map_path}")
                self.create_placeholder_map()
        else:
            logger.warning(f"지도 이미지를 찾을 수 없습니다: {self.map_path}")
            self.create_placeholder_map()

        # 지도 이미지 표시
        self.update_map_image()
        
        # 마커 위치 업데이트
        self.update_marker_positions()

    def create_placeholder_map(self):
        """임시 지도 이미지 생성"""
        self.map_pixmap = QPixmap(960, 720)
        self.map_pixmap.fill(Qt.GlobalColor.lightGray)
        
        # 텍스트 추가
        painter = QPainter(self.map_pixmap)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawText(self.map_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 
                        "지도 이미지를 로드할 수 없습니다\n경로를 확인하세요")
        painter.end()
        
        # 임시 이미지 저장
        try:
            self.map_pixmap.save(self.map_path)
            logger.info(f"임시 지도 이미지가 생성되었습니다: {self.map_path}")
        except Exception as e:
            logger.error(f"임시 지도 이미지 저장 실패: {str(e)}")

    def update_map_image(self):
        """지도 이미지 업데이트"""
        if not self.map_pixmap.isNull():
            # 이미지 스케일링 및 설정
            scaled_pixmap = self.map_pixmap.scaled(
                self.map_width, self.map_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.label_map.setPixmap(scaled_pixmap)
            logger.debug(f"지도 이미지 업데이트 완료: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
        else:
            logger.warning("지도 이미지가 null임")
        
    def create_marker_data(self, obj: DetectedObject) -> MarkerData:
        """DetectedObject로부터 MarkerData 생성"""
        return MarkerData(
            object_id=obj.object_id,
            x=obj.x_coord,
            y=obj.y_coord,
            object_type=obj.object_type.value,
            zone=obj.zone.value
        )
        
    def add_dynamic_marker(self, marker_data: MarkerData):
        """동적 마커 추가"""
        try:
            # 기존 마커가 있으면 제거
            if marker_data.object_id in self.markers:
                self.remove_marker(marker_data.object_id)
                
            # 새 마커 생성
            marker = DynamicMarker(marker_data, self)
            marker.clicked.connect(lambda: self.marker_clicked.emit(marker_data.object_id))
            
            # 위치 계산 및 설정
            x, y = self.calculate_marker_position(marker_data.x, marker_data.y)
            marker.move(x, y)
            marker.show()
            
            self.markers[marker_data.object_id] = marker
            logger.debug(f"마커 추가 성공: ID {marker_data.object_id}")
            
            # ID 라벨 추가
            id_label = QLabel(f"ID:{marker_data.object_id}", self)
            id_label.setStyleSheet("""
                background: rgba(0,0,0,0.7);
                color: white;
                border-radius: 6px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 12px;
            """)
            id_label.adjustSize()
            # 마커 중앙 상단에 위치 (마커 크기 50px 고려)
            label_x = x + 25 - id_label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
            label_y = y - id_label.height() - 2     # 마커 상단에서 2px 위
            id_label.move(label_x, label_y)
            id_label.show()
            self.marker_labels[marker_data.object_id] = id_label
            
        except Exception as e:
            logger.error(f"마커 추가 실패: {str(e)}")
            
    def update_marker(self, marker_data: MarkerData):
        """마커 업데이트"""
        try:
            if marker_data.object_id in self.markers:
                marker = self.markers[marker_data.object_id]
                marker.data = marker_data
                
                # 위치가 변경되었으면 이동
                x, y = self.calculate_marker_position(marker_data.x, marker_data.y)
                marker.animate_to_position(x, y)
                
                # 라벨 위치도 업데이트
                label = self.marker_labels.get(marker_data.object_id)
                if label:
                    label_x = x + 25 - label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
                    label_y = y - label.height() - 2     # 마커 상단에서 2px 위
                    label.move(label_x, label_y)
                
                # 외관 업데이트
                marker.update_appearance()
                
                logger.debug(f"마커 업데이트 성공: ID {marker_data.object_id}")
        except Exception as e:
            logger.error(f"마커 업데이트 실패: {str(e)}")
            
    def remove_marker(self, object_id: int):
        """마커 제거"""
        try:
            if object_id in self.markers:
                marker = self.markers[object_id]
                marker.hide()
                marker.deleteLater()
                del self.markers[object_id]
                
                if self.selected_marker_id == object_id:
                    self.selected_marker_id = None
                    
                # 라벨 제거
                if object_id in self.marker_labels:
                    self.marker_labels[object_id].hide()
                    self.marker_labels[object_id].deleteLater()
                    del self.marker_labels[object_id]
                    
                logger.debug(f"마커 제거 성공: ID {object_id}")
        except Exception as e:
            logger.error(f"마커 제거 실패: {str(e)}")
            
    def select_marker(self, object_id: int):
        """마커 선택"""
        try:
            # 이전 선택 해제
            if self.selected_marker_id is not None and self.selected_marker_id in self.markers:
                self.markers[self.selected_marker_id].data.state = 'NORMAL'
                self.markers[self.selected_marker_id].update_appearance()
            
            # 새로운 마커 선택
            if object_id in self.markers:
                self.selected_marker_id = object_id
                self.markers[object_id].data.state = 'SELECTED'
                self.markers[object_id].update_appearance()
                logger.debug(f"마커 선택 성공: ID {object_id}")
        except Exception as e:
            logger.error(f"마커 선택 실패: {str(e)}")
            
    def clear_markers(self):
        """모든 마커 제거"""
        try:
            for marker in self.markers.values():
                marker.hide()
                marker.deleteLater()
            self.markers.clear()
            
            # 라벨도 함께 제거
            for label in self.marker_labels.values():
                label.hide()
                label.deleteLater()
            self.marker_labels.clear()
            
            self.selected_marker_id = None
            logger.debug("모든 마커 제거 완료")
        except Exception as e:
            logger.error(f"마커 제거 실패: {str(e)}")
            
    def calculate_marker_position(self, map_x: float, map_y: float) -> Tuple[int, int]:
        """지도 좌표를 위젯 좌표로 변환"""
        x = int(map_x * self.width() / self.map_width)
        y = int(map_y * self.height() / self.map_height)
        return x - 12, y - 12  # 마커 크기의 절반만큼 조정
        
    def update_marker_positions(self):
        """모든 마커 위치 업데이트 (위젯 크기 변경 시)"""
        for marker in self.markers.values():
            x, y = self.calculate_marker_position(marker.data.x, marker.data.y)
            if not marker.is_animating:
                marker.move(x, y)
            # 라벨도 같이 이동 (마커 중앙 상단에 위치)
            label = self.marker_labels.get(marker.data.object_id)
            if label:
                label_x = x + 25 - label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
                label_y = y - label.height() - 2     # 마커 상단에서 2px 위
                label.move(label_x, label_y)
                
    def resizeEvent(self, event):
        """위젯 크기 변경 시 처리"""
        super().resizeEvent(event)
        self.update_marker_positions()
