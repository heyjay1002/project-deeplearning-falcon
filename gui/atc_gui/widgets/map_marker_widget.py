from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont
import os
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from utils.logger import logger

class MarkerType(Enum):
    """마커 타입"""
    BIRD = "bird"
    AIRCRAFT = "aircraft"
    VEHICLE = "vehicle"
    DEBRIS = "debris"
    PERSON = "person"
    ANIMAL = "animal"
    FIRE = "fire"
    WORK_PERSON = "work_person"
    WORK_VEHICLE = "work_vehicle"
    UNKNOWN = "unknown"

class MarkerState(Enum):
    """마커 상태"""
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"
    SELECTED = "selected"

@dataclass
class MarkerData:
    """마커 데이터"""
    marker_id: int
    x: float  # 지도 좌표 (0.0 ~ 1.0)
    y: float  # 지도 좌표 (0.0 ~ 1.0)
    marker_type: MarkerType
    state: MarkerState = MarkerState.NORMAL
    label: str = ""
    icon_path: Optional[str] = None
    size: int = 24
    
class DynamicMarker(QLabel):
    """동적 마커 위젯"""
    clicked = pyqtSignal(int)  # marker_id 전달
    
    def __init__(self, data: MarkerData, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_animating = False
        self.animation = None
        
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
        if self.data.state != MarkerState.NORMAL:
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
        
        # 마커 타입별 색상
        color_map = {
            MarkerType.BIRD: QColor("#FF6B6B"),
            MarkerType.AIRCRAFT: QColor("#4ECDC4"),
            MarkerType.VEHICLE: QColor("#45B7D1"),
            MarkerType.DEBRIS: QColor("#FFA07A"),
            MarkerType.UNKNOWN: QColor("#95A5A6")
        }
        
        color = color_map.get(self.data.marker_type, QColor("#95A5A6"))
        
        # 원형 마커 그리기
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        
        margin = 2
        painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
        
        # 라벨이 있으면 텍스트 추가
        if self.data.label:
            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont()
            font.setPixelSize(max(8, size // 3))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.data.label)
        
        painter.end()
        return pixmap
        
    def add_state_effect(self, pixmap: QPixmap) -> QPixmap:
        """상태 효과 추가"""
        if self.data.state == MarkerState.SELECTED:
            # 선택된 마커는 테두리 강조
            enhanced = QPixmap(pixmap.size())
            enhanced.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(enhanced)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 글로우 효과
            painter.setPen(QPen(QColor("#FFD700"), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(2, 2, pixmap.width() - 4, pixmap.height() - 4)
            
            # 원본 마커 그리기
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            return enhanced
            
        elif self.data.state in [MarkerState.WARNING, MarkerState.DANGER]:
            # 경고/위험 상태는 깜빡임 효과 (애니메이션에서 처리)
            pass
            
        return pixmap
    
    def animate_to_position(self, x: int, y: int, duration: int = 1000):
        """위치로 애니메이션 이동"""
        if self.animation:
            self.animation.stop()
            
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(QRect(x, y, self.width(), self.height()))
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.is_animating = True
        self.animation.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.animation.start()
    
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
        self.setVisible(self.blink_visible)
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data.marker_id)
        super().mousePressEvent(event)

class MapMarkerWidget(QWidget):
    """향상된 지도 마커 위젯"""
    marker_clicked = pyqtSignal(int)  # marker_id 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.markers: Dict[int, DynamicMarker] = {}
        self.map_size = (800, 600)  # 기본 지도 크기
        self.widget_size = (800, 600)  # 위젯 크기
        
    def set_map_size(self, width: int, height: int):
        """지도 크기 설정"""
        self.map_size = (width, height)
        self.update_marker_positions()
        
    def set_map_image(self, image_path: str):
        """지도 이미지 설정 (호환성을 위한 메서드)"""
        # 기존 인터페이스와의 호환성을 위해 유지
        # 실제로는 배경 지도는 다른 레이어에서 처리됨
        pass
        
    def resizeEvent(self, event):
        """위젯 크기 변경 시"""
        super().resizeEvent(event)
        self.widget_size = (event.size().width(), event.size().height())
        self.update_marker_positions()
    
    def add_marker(self, x: float, y: float, icon_path: str, row_idx: int, 
                  callback: Callable, icon_size: int = 24) -> bool:
        """기존 인터페이스와 호환성을 위한 마커 추가 메서드"""
        # 기존 파라미터를 새로운 형식으로 변환
        marker_data = MarkerData(
            marker_id=row_idx,
            x=x,
            y=y,
            marker_type=MarkerType.UNKNOWN,
            state=MarkerState.NORMAL,
            label=str(row_idx),
            icon_path=icon_path,
            size=icon_size
        )
        
        return self.add_dynamic_marker(marker_data, animate=True)
    
    def add_dynamic_marker(self, data: MarkerData, animate: bool = True) -> bool:
        """새로운 동적 마커 추가"""
        try:
            # 기존 마커가 있으면 제거
            if data.marker_id in self.markers:
                self.remove_marker(data.marker_id)
                
            # 새 마커 생성
            marker = DynamicMarker(data, self)
            marker.clicked.connect(self.marker_clicked.emit)
            
            # 위치 계산 및 설정
            x, y = self.calculate_marker_position(data.x, data.y)
            
            if animate and data.marker_id in self.markers:
                # 기존 마커가 있었다면 애니메이션으로 이동
                marker.move(self.markers[data.marker_id].x(), self.markers[data.marker_id].y())
                marker.show()
                marker.animate_to_position(x, y)
            else:
                # 새 마커는 바로 위치 설정
                marker.move(x, y)
                marker.show()
            
            # 상태에 따른 효과 적용
            if data.state in [MarkerState.WARNING, MarkerState.DANGER]:
                marker.start_blinking()
            
            self.markers[data.marker_id] = marker
            return True
            
        except Exception as e:
            logger.error(f"마커 추가 오류: {e}")
            return False
    
    def update_marker(self, data: MarkerData, animate: bool = True) -> bool:
        """마커 업데이트"""
        if data.marker_id not in self.markers:
            return self.add_dynamic_marker(data, animate)
            
        marker = self.markers[data.marker_id]
        old_data = marker.data
        marker.data = data
        
        # 위치가 변경되었으면 이동
        if old_data.x != data.x or old_data.y != data.y:
            x, y = self.calculate_marker_position(data.x, data.y)
            if animate:
                marker.animate_to_position(x, y)
            else:
                marker.move(x, y)
        
        # 외관이 변경되었으면 업데이트
        if (old_data.marker_type != data.marker_type or 
            old_data.state != data.state or 
            old_data.icon_path != data.icon_path):
            marker.update_appearance()
            
            # 깜빡임 효과 관리
            if data.state in [MarkerState.WARNING, MarkerState.DANGER]:
                marker.start_blinking()
            else:
                marker.stop_blinking()
                
        return True
    
    def remove_marker(self, marker_id: int) -> bool:
        """마커 제거"""
        if marker_id in self.markers:
            marker = self.markers[marker_id]
            marker.stop_blinking()
            marker.hide()
            marker.deleteLater()
            del self.markers[marker_id]
            return True
        return False
    
    def clear_markers(self):
        """모든 마커 제거"""
        for marker_id in list(self.markers.keys()):
            self.remove_marker(marker_id)
    
    def calculate_marker_position(self, map_x: float, map_y: float) -> Tuple[int, int]:
        """지도 좌표를 위젯 좌표로 변환"""
        # 지도 좌표 (0.0~1.0)를 위젯 좌표로 변환
        widget_x = int(map_x * self.widget_size[0])
        widget_y = int(map_y * self.widget_size[1])
        
        # 마커가 위젯 경계를 벗어나지 않도록 조정
        marker_size = 24  # 기본 마커 크기
        widget_x = max(0, min(widget_x - marker_size // 2, self.widget_size[0] - marker_size))
        widget_y = max(0, min(widget_y - marker_size // 2, self.widget_size[1] - marker_size))
        
        return widget_x, widget_y
    
    def update_marker_positions(self):
        """모든 마커 위치 업데이트 (위젯 크기 변경 시)"""
        for marker in self.markers.values():
            x, y = self.calculate_marker_position(marker.data.x, marker.data.y)
            if not marker.is_animating:  # 애니메이션 중이 아닐 때만
                marker.move(x, y)
    
    def select_marker(self, marker_id: int):
        """마커 선택"""
        # 모든 마커 선택 해제
        for marker in self.markers.values():
            if marker.data.state == MarkerState.SELECTED:
                marker.data.state = MarkerState.NORMAL
                marker.update_appearance()
        
        # 해당 마커 선택
        if marker_id in self.markers:
            marker = self.markers[marker_id]
            marker.data.state = MarkerState.SELECTED
            marker.update_appearance()
    
    def get_marker_count_by_type(self) -> Dict[MarkerType, int]:
        """타입별 마커 개수 반환"""
        count = {}
        for marker in self.markers.values():
            marker_type = marker.data.marker_type
            count[marker_type] = count.get(marker_type, 0) + 1
        return count
    
    # 기존 인터페이스와의 호환성을 위한 메서드들
    def move_marker(self, marker_idx: int, new_x: float, new_y: float) -> bool:
        """마커 이동 (기존 인터페이스 호환)"""
        if marker_idx in self.markers:
            marker = self.markers[marker_idx]
            marker.data.x = new_x
            marker.data.y = new_y
            x, y = self.calculate_marker_position(new_x, new_y)
            marker.animate_to_position(x, y)
            return True
        return False
    
    def get_marker(self, marker_idx: int):
        """마커 정보 조회 (기존 인터페이스 호환)"""
        return self.markers.get(marker_idx)
    
    def get_marker_count(self) -> int:
        """마커 개수 반환 (기존 인터페이스 호환)"""
        return len(self.markers)