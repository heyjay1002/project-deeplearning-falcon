from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont
import os
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from utils.logger import logger
from config import ObjectType
from utils.interface import DetectedObject

class MarkerState(Enum):
    """마커 상태"""
    NORMAL = "normal"    # 일반적인 객체 감지 상태
    WARNING = "warning"  # 구조가 필요한 사람 감지 상태
    SELECTED = "selected"  # 사용자가 선택한 상태

@dataclass
class MarkerData:
    """마커 데이터"""
    object_id: str
    object_type: ObjectType
    x: float
    y: float    
    state: MarkerState = MarkerState.NORMAL    
    icon_path: str
    size: int = 24
    rescue_status: Optional[str] = None
    
class DynamicMarker(QLabel):
    """동적 마커 위젯"""
    clicked = pyqtSignal(int)   # object_id 전달
    
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
        
        # 객체 타입별 아이콘 경로 매핑
        icon_paths = {
            ObjectType.BIRD: "gui/atc_gui/resources/images/bird.png",
            ObjectType.FOD: "gui/atc_gui/resources/images/fod.png",
            ObjectType.PERSON: "gui/atc_gui/resources/images/person.png",
            ObjectType.ANIMAL: "gui/atc_gui/resources/images/animal.png",
            ObjectType.VEHICLE: "gui/atc_gui/resources/images/vehicle.png",
            ObjectType.WORK_PERSON: "gui/atc_gui/resources/images/worker.png",
            ObjectType.WORK_VEHICLE: "gui/atc_gui/resources/images/vehicle_work.png"
        }
        
        # 아이콘 로드 시도
        icon_path = icon_paths.get(self.data.object_type)
        if icon_path and os.path.exists(icon_path):
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
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
                if self.data.state == MarkerState.WARNING:
                    painter.setPen(QPen(QColor("#FFA500"), 2))  # 주황색
                elif self.data.state == MarkerState.SELECTED:
                    painter.setPen(QPen(QColor("#FFD700"), 2))  # 금색
                else:
                    painter.setPen(QPen(QColor("#FFFFFF"), 2))  # 흰색
                    
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(2, 2, size - 4, size - 4, 8, 8)
                
                # 객체 ID가 있으면 텍스트 추가
                if self.data.object_id:
                    painter.setPen(QPen(Qt.GlobalColor.white))
                    font = QFont()
                    font.setPixelSize(max(8, size // 3))
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.data.object_id)
                
                painter.end()
                return pixmap
        
        # 아이콘 로드 실패 시 기본 마커 생성
        default_color = QColor("#4A90E2")  # 기본 파란색
        
        # 기본 마커 그리기
        painter.setBrush(QBrush(default_color))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        
        # 둥근 모서리 사각형 그리기
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 8, 8)
        
        # 객체 ID 텍스트 추가
        if self.data.object_id:
            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont()
            font.setPixelSize(max(8, size // 3))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.data.object_id)
        
        painter.end()
        return pixmap
        
    def add_state_effect(self, pixmap: QPixmap) -> QPixmap:
        """상태 효과 추가"""
        if self.data.state == MarkerState.SELECTED:
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
            
        elif self.data.state in [MarkerState.WARNING]:
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
    
    def animate_to_position(self, x: int, y: int, duration: int = 1000):
        """현재위치로 애니메이션 이동"""
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
        self.map_size = (960, 720)  # 기본 지도 크기
        
    def set_map_size(self, width: int, height: int):
        """지도 크기 설정"""
        self.map_size = (width, height)
        self.update_marker_positions()
        
    def set_map_image(self, image_path: str):
        """지도 이미지 설정 (호환성을 위한 메서드)"""
        base_dir = os.path.dirname(__file__)
        self.map_path = os.path.join(base_dir, '../resources/images/map_crop.png')

        self.map_pixmap = QPixmap()
        
        if os.path.exists(self.map_path):
            if self.map_pixmap.load(self.map_path):
                pass  # 로드 성공
            else:
                # 임시 이미지 생성
                self.create_placeholder_map()
        else:
            # 임시 이미지 생성
            self.create_placeholder_map()

        # 초기 이미지 표시
        self.update_map_image()

    def create_placeholder_map(self):
        """임시 지도 이미지 생성"""
        self.map_pixmap = QPixmap(960, 720)
        self.map_pixmap.fill(Qt.GlobalColor.lightGray)
        
        # 텍스트 추가
        from PyQt6.QtGui import QPainter, QPen
        painter = QPainter(self.map_pixmap)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawText(self.map_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 
                        "지도 이미지를 로드할 수 없습니다\n경로를 확인하세요")
        painter.end()

    def update_map_image(self):
        """지도 이미지 업데이트"""
        if not self.map_pixmap.isNull():
            target_size = (960, 720)
            # 이미지 스케일링 및 설정
            scaled_pixmap = self.map_pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.label_map.setPixmap(scaled_pixmap)
            logger.debug(f"지도 이미지 업데이트 완료: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
        else:
            logger.warning("지도 이미지가 null임")
        
    def resizeEvent(self, event):
        """위젯 크기 변경 시"""
        super().resizeEvent(event)
        self.widget_size = (event.size().width(), event.size().height())
        self.update_marker_positions()   
    
    def create_marker_data(self, obj: DetectedObject) -> MarkerData:
        """DetectedObject를 MarkerData로 변환"""
        # 기본 상태는 NORMAL
        marker_state = MarkerState.NORMAL
        
        # 사람이면서 구조 정보가 있는 경우 WARNING 상태로 설정
        if obj.object_type in [ObjectType.PERSON, ObjectType.WORK_PERSON] and hasattr(obj, 'rescue') and obj.rescue:
            marker_state = MarkerState.WARNING
              
        # 마커 크기는 항상 24로 고정
        marker_size = 24
        
        # 객체 타입별 아이콘 경로 매핑
        icon_paths = {
            ObjectType.BIRD: "gui/atc_gui/resources/images/bird.png",
            ObjectType.FOD: "gui/atc_gui/resources/images/fod.png",
            ObjectType.PERSON: "gui/atc_gui/resources/images/person.png",
            ObjectType.ANIMAL: "gui/atc_gui/resources/images/animal.png",
            ObjectType.VEHICLE: "gui/atc_gui/resources/images/vehicle.png",
            ObjectType.WORK_PERSON: "gui/atc_gui/resources/images/worker.png",
            ObjectType.WORK_VEHICLE: "gui/atc_gui/resources/images/vehicle_work.png"
        }
        
        return MarkerData(
            object_id=obj.object_id,
            object_type=obj.object_type,
            x=obj.x_coord,
            y=obj.y_coord,
            state=marker_state,
            icon_path=icon_paths.get(obj.object_type),
            size=marker_size,
            rescue_status=obj.extra_info.rescue_status if obj.extra_info else None
        )

    def add_marker(self, obj: DetectedObject, animate: bool = True) -> bool:
        """DetectedObject를 받아 마커 추가"""
        try:
            # 마커 데이터 생성
            marker_data = self.create_marker_data(obj)
            
            # 기존 마커가 있으면 제거
            if obj.object_id in self.markers:
                self.remove_marker(obj.object_id)
                
            # 새 마커 생성
            marker = DynamicMarker(marker_data, self)
            marker.clicked.connect(self.marker_clicked.emit)
            
            # 위치 계산 및 설정
            x, y = self.calculate_marker_position(marker_data.x, marker_data.y)
            
            if animate and obj.object_id in self.markers:
                # 기존 마커가 있었다면 애니메이션으로 이동
                marker.move(self.markers[obj.object_id].x(), self.markers[obj.object_id].y())
                marker.show()
                marker.animate_to_position(x, y)
            else:
                # 새 마커는 바로 위치 설정
                marker.move(x, y)
                marker.show()
            
            # 상태에 따른 효과 적용
            if marker_data.state == MarkerState.WARNING:
                marker.start_blinking()
            
            self.markers[obj.object_id] = marker
            return True
            
        except Exception as e:
            logger.error(f"마커 추가 오류: {e}")
            return False
    
    def update_marker(self, data: MarkerData, animate: bool = True) -> bool:
        """마커 업데이트"""
        if data.object_id not in self.markers:
            return self.add_marker(data, animate)
            
        marker = self.markers[data.object_id]
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
        if (old_data.object_type != data.object_type or 
            old_data.state != data.state or 
            old_data.icon_path != data.icon_path):
            marker.update_appearance()
            
            # 깜빡임 효과 관리
            if data.state in [MarkerState.WARNING]:
                marker.start_blinking()
            else:
                marker.stop_blinking()
                
        return True
    
    def remove_marker(self, object_id: int) -> bool:
        """마커 제거"""
        if object_id in self.markers:
            marker = self.markers[object_id]
            marker.stop_blinking()
            marker.hide()
            marker.deleteLater()
            del self.markers[object_id]
            return True
        return False
    
    def clear_markers(self):
        """모든 마커 제거"""
        for object_id in list(self.markers.keys()):
            self.remove_marker(object_id)
    
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
    
    def select_marker(self, object_id: int):
        """마커 선택"""
        # 모든 마커 선택 해제
        for marker in self.markers.values():
            if marker.data.state == MarkerState.SELECTED:
                marker.data.state = MarkerState.NORMAL
                marker.update_appearance()
        
        # 해당 마커 선택
        if object_id in self.markers:
            marker = self.markers[object_id]
            marker.data.state = MarkerState.SELECTED
            marker.update_appearance()
    
    def get_marker_count_by_type(self) -> Dict[MarkerType, int]:
        """타입별 마커 개수 반환"""
        count = {}
        for marker in self.markers.values():
            marker_type = marker.data.object_type
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