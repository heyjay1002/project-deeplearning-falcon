from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar
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
    size: int = 50
    icon_path: Optional[str] = None
    state: str = 'NORMAL'  # NORMAL, WARNING, SELECTED
    rescue_level: int = 0  # 구조 레벨 (위험도)
    
    @property
    def is_selected(self) -> bool:
        """선택 상태 확인"""
        return self.state == 'SELECTED'

class DynamicMarker(QLabel):
    """동적 마커 위젯"""
    clicked = pyqtSignal(int)   # object_id 전달
    
    def __init__(self, data: MarkerData, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_animating = False
        
        # 애니메이션 객체를 부모와 연결하여 메모리 누수 방지
        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._animation_finished)
        
        # 깜빡임 타이머 초기화
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.toggle_visibility)
        self.blink_visible = True
        
        # 마커 설정
        self.setup_marker()
        
    def get_marker_size(self) -> int:
        """마커 크기 반환"""
        return self.data.size
    
    def get_marker_half_size(self) -> int:
        """마커 크기의 절반 반환"""
        return self.data.size // 2
        
    def setup_marker(self):
        """마커 초기 설정"""
        # 크기 설정
        self.setFixedSize(self.data.size, self.data.size)
        
        # 마커 이미지 생성
        self.update_appearance()
        
        # 클릭 가능하도록 설정
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 마커가 클릭 가능하도록 설정
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.raise_()
        
        logger.debug(f"마커 설정 완료: ID {self.data.object_id}, 크기: {self.data.size}x{self.data.size}")
        
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
            ObjectType.ANIMAL.value: os.path.join(base_path, 'resources/images/animal2.png'),
            ObjectType.AIRPLANE.value: os.path.join(base_path, 'resources/images/airplane.png'),
            ObjectType.VEHICLE.value: os.path.join(base_path, 'resources/images/vehicle_work.png'),
            ObjectType.WORK_PERSON.value: os.path.join(base_path, 'resources/images/worker.png'),
            ObjectType.WORK_VEHICLE.value: os.path.join(base_path, 'resources/images/vehicle.png'),
            ObjectType.UNKNOWN.value: os.path.join(base_path, 'resources/images/unknown.png')
        }
        
        # 안전한 객체 타입 처리
        obj_type = self.data.object_type
        if obj_type is None:
            obj_type_key = ObjectType.UNKNOWN.value
        elif hasattr(obj_type, 'value'):
            obj_type_key = obj_type.value
        else:
            obj_type_key = str(obj_type)
            
        icon_path = icon_paths.get(obj_type_key)
        
        if icon_path and os.path.exists(icon_path):
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
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
                
                # 상태에 따른 테두리 추가 (SELECTED만 유지)
                if self.data.state == 'SELECTED':
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
        self.blink_timer.start(500)  # 0.5초 간격
        
    def stop_blinking(self):
        """깜빡임 효과 중지"""
        self.blink_timer.stop()
        self.setVisible(True)
        self.blink_visible = True
        self.update_appearance()
    
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
        self.marker_labels: Dict[int, QLabel] = {}  # ID 라벨
        self.risk_labels: Dict[int, QWidget] = {}   # 위험도 라벨 (게이지바 포함)
        self.selected_marker_id: Optional[int] = None

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # 기본 지도 크기 설정
        self.map_width = 960
        self.map_height = 720
        self.set_map_size(self.map_width, self.map_height)
        
        # 지도 이미지를 표시할 라벨 생성
        self.label_map = QLabel(self)
        self.label_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_map.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
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
        self.map_path = os.path.join(os.path.dirname(__file__), '../resources/images/map.png')
        self.map_pixmap = QPixmap()
        
        if os.path.exists(self.map_path):
            self.map_pixmap.load(self.map_path)
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
        
    def create_marker_data(self, obj: DetectedObject) -> dict:
        """DetectedObject로부터 MarkerData 생성"""
        return {
            'object_id': obj.object_id,
            'object_type': obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type),
            'x_coord': obj.x_coord,
            'y_coord': obj.y_coord,
            'area': obj.area.value if hasattr(obj.area, 'value') else str(obj.area),
            'timestamp': obj.timestamp,
            'image_data': obj.image_data,
            'rescue_level': obj.state_info if obj.state_info else 0
        }
        
    def calculate_marker_position(self, map_x: float, map_y: float, marker_size: int = 50) -> Tuple[int, int]:
        """지도 좌표를 위젯 좌표로 변환"""
        # 안전한 나누기 연산을 위한 검사 (0으로 나누는 것 방지)
        widget_width = max(1, self.width())
        widget_height = max(1, self.height())
        map_width = max(1, self.map_width)
        map_height = max(1, self.map_height)
        
        # 지도 좌표를 위젯 좌표로 변환
        x = int(map_x * widget_width / map_width)
        y = int(map_y * widget_height / map_height)
        
        # 마커 크기의 절반만큼 조정 (마커 중앙이 좌표에 오도록)
        marker_half_size = marker_size // 2
        
        # 경계 제약 조건 적용
        x = self._constrain_position(x, marker_half_size, widget_width)
        y = self._constrain_position(y, marker_half_size, widget_height)
        
        return x - marker_half_size, y - marker_half_size
    
    def _constrain_position(self, position: int, margin: int, max_size: int) -> int:
        """위치를 경계 내로 제한"""
        constrained_position = max(margin, min(position, max_size - margin))
        return constrained_position
    
    def _on_marker_clicked(self, object_id: int):
        """마커 클릭 시 호출되는 메서드"""
        # 마커 선택
        self.select_marker(object_id)
        
        # 외부로 시그널 전달
        self.marker_clicked.emit(object_id)
    
    def create_risk_gauge_widget(self, rescue_level: int, parent=None) -> QWidget:
        """위험도 게이지바 위젯 생성 (세로 배치, 텍스트 라벨 가로 길이 짧게)"""
        risk_widget = QWidget(parent)
        risk_layout = QVBoxLayout(risk_widget)
        risk_layout.setContentsMargins(2, 2, 2, 2)
        risk_layout.setSpacing(2)
        
        # "위험도" 텍스트 라벨
        risk_text_label = QLabel("위험도")
        risk_text_label.setStyleSheet("""
            QLabel {
                background: rgba(0,0,0,0.8);
                color: white;
                border-radius: 4px;
                padding: 1px 4px;
                font-weight: bold;
                font-size: 10px;
                min-width: 24px;
                max-width: 40px;
            }
        """)
        risk_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        risk_text_label.adjustSize()
        
        # 게이지바
        gauge = QProgressBar()
        gauge.setRange(0, 10)  # 0-10 범위
        gauge.setValue(rescue_level)
        gauge.setFixedSize(40, 8)
        gauge.setTextVisible(False)  # 텍스트 숨김
        
        # 게이지바 색상: 항상 빨간색
        gauge.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                border-radius: 3px;
            }
        """)
        
        risk_layout.addWidget(risk_text_label)
        risk_layout.addWidget(gauge)
        
        return risk_widget
    
    def add_dynamic_marker(self, marker_data: dict):
        """동적 마커 추가"""
        try:
            # 기존 마커의 상태 정보 보존
            existing_state = 'NORMAL'
            if marker_data['object_id'] in self.markers:
                existing_state = self.markers[marker_data['object_id']].data.state
                self.remove_marker(marker_data['object_id'])
                
            # 새 마커 생성 (기존 상태 보존)
            marker = DynamicMarker(MarkerData(
                object_id=marker_data['object_id'],
                x=marker_data['x_coord'],
                y=marker_data['y_coord'],
                object_type=marker_data['object_type'],
                zone=marker_data['area'],
                state=existing_state,  # 기존 상태 정보 유지
                rescue_level=marker_data.get('rescue_level', 0)  # 구조 레벨 추가
            ), self)
            marker.clicked.connect(lambda object_id: self._on_marker_clicked(object_id))
            
            # 위치 계산 및 설정 (경계 제약 적용됨)
            x, y = self.calculate_marker_position(marker_data['x_coord'], marker_data['y_coord'], 50)
            marker.move(x, y)
            
            marker.show()
            marker.raise_()
            
            self.markers[marker_data['object_id']] = marker
            logger.debug(f"마커 추가 성공: ID {marker_data['object_id']}, 위치: ({x}, {y}), 상태: {existing_state}")
            
            # ID 라벨 추가
            id_label = QLabel(f"ID:{marker_data['object_id']}", self)
            id_label.setStyleSheet("""
                background: rgba(0,0,0,0.7);
                color: white;
                border-radius: 6px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 12px;
            """)
            id_label.adjustSize()
            
            # 라벨 위치 계산 (마커 중앙 상단, 경계 제약 적용)
            marker_half_size = 50 // 2
            label_x = x + marker_half_size - id_label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
            label_y = y - id_label.height() - 2     # 마커 상단에서 2px 위
            
            # 라벨도 경계 제약 적용
            label_x = self._constrain_position(label_x, 0, self.width() - id_label.width())
            label_y = self._constrain_position(label_y, 0, self.height() - id_label.height())
            
            id_label.move(label_x, label_y)
            id_label.show()
            id_label.raise_()

            id_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            
            self.marker_labels[marker_data['object_id']] = id_label
            
            # 위험도 게이지바 추가 (PERSON, WORK_PERSON 객체만)
            logger.debug(f"위험도 게이지바 체크: object_type={marker_data['object_type']}, rescue_level={marker_data.get('rescue_level', 0)}")
            if marker_data['object_type'] in ['일반인', '작업자']:
                rescue_level = marker_data.get('rescue_level', 0)
                logger.debug(f"PERSON/WORK_PERSON 객체 발견: ID={marker_data['object_id']}, rescue_level={rescue_level}")
                if rescue_level > 0:  # 위험도가 0보다 클 때만 표시
                    logger.debug(f"위험도 게이지바 생성 시작: ID={marker_data['object_id']}, rescue_level={rescue_level}")
                    risk_widget = self.create_risk_gauge_widget(rescue_level, parent=self)
                    risk_widget.adjustSize()  # 크기 계산
                    
                    # 위험도 라벨 위치 계산 (ID 라벨 위에 배치, 마커 기준 가운데 정렬)
                    risk_x = x + marker_half_size - risk_widget.width()//2
                    risk_y = label_y - risk_widget.height() - 2
                    
                    # 경계 제약 적용
                    risk_x = self._constrain_position(risk_x, 0, self.width() - risk_widget.width())
                    risk_y = self._constrain_position(risk_y, 0, self.height() - risk_widget.height())
                    
                    risk_widget.move(risk_x, risk_y)
                    risk_widget.show()
                    risk_widget.raise_()
                    risk_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    
                    self.risk_labels[marker_data['object_id']] = risk_widget
                    logger.debug(f"위험도 게이지바 생성 완료: ID={marker_data['object_id']}, 위치=({risk_x}, {risk_y})")
                else:
                    logger.debug(f"위험도가 0이므로 게이지바 미생성: ID={marker_data['object_id']}")
            else:
                logger.debug(f"PERSON/WORK_PERSON이 아닌 객체: {marker_data['object_type']}")
        except Exception as e:
            logger.error(f"마커 추가 실패: {str(e)}")
            
    def update_marker(self, marker_data: dict):
        """마커 업데이트"""
        try:
            if marker_data['object_id'] in self.markers:
                marker = self.markers[marker_data['object_id']]
                
                # 기존 상태 정보 보존
                current_state = marker.data.state
                
                marker.data = MarkerData(
                    object_id=marker_data['object_id'],
                    x=marker_data['x_coord'],
                    y=marker_data['y_coord'],
                    object_type=marker_data['object_type'],
                    zone=marker_data['area'],
                    state=current_state,  # 기존 상태 정보 유지
                    rescue_level=marker_data.get('rescue_level', 0)  # 구조 레벨 추가
                )
                
                # 위치가 변경되었으면 이동 (경계 제약 적용됨)
                x, y = self.calculate_marker_position(marker_data['x_coord'], marker_data['y_coord'], 50)
                marker.animate_to_position(x, y)
                
                # 라벨 위치도 업데이트 (경계 제약 적용)
                label = self.marker_labels.get(marker_data['object_id'])
                if label:
                    marker_half_size = 50 // 2
                    label_x = x + marker_half_size - label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
                    label_y = y - label.height() - 2     # 마커 상단에서 2px 위
                    
                    # 라벨도 경계 제약 적용
                    label_x = self._constrain_position(label_x, 0, self.width() - label.width())
                    label_y = self._constrain_position(label_y, 0, self.height() - label.height())
                    
                    label.move(label_x, label_y)

                # 위험도 게이지바 업데이트 (PERSON, WORK_PERSON 객체만)
                if marker_data['object_type'] in ['일반인', '작업자']:
                    rescue_level = marker_data.get('rescue_level', 0)
                    risk_widget = self.risk_labels.get(marker_data['object_id'])
                    
                    if rescue_level > 0:
                        if risk_widget is None:
                            # 위험도 게이지바가 없으면 새로 생성
                            risk_widget = self.create_risk_gauge_widget(rescue_level, parent=self)
                            self.risk_labels[marker_data['object_id']] = risk_widget
                            risk_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                        
                        # 위험도 게이지바 위치 업데이트
                        marker_half_size = 50 // 2
                        label = self.marker_labels.get(marker_data['object_id'])
                        if label:
                            label_y = label.y()
                            risk_x = x + marker_half_size - risk_widget.width()//2
                            risk_y = label_y - risk_widget.height() - 2
                            
                            # 경계 제약 적용
                            risk_x = self._constrain_position(risk_x, 0, self.width() - risk_widget.width())
                            risk_y = self._constrain_position(risk_y, 0, self.height() - risk_widget.height())
                            
                            risk_widget.move(risk_x, risk_y)
                            risk_widget.show()
                            risk_widget.raise_()
                    else:
                        # 위험도가 0이면 게이지바 제거
                        if risk_widget:
                            risk_widget.hide()
                            risk_widget.deleteLater()
                            del self.risk_labels[marker_data['object_id']]

                marker.raise_()
                
                # 외관 업데이트
                marker.update_appearance()
                
                logger.debug(f"마커 업데이트 성공: ID {marker_data['object_id']}, 위치: ({x}, {y}), 상태: {current_state}")
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
                
                # 라벨 제거
                if object_id in self.marker_labels:
                    self.marker_labels[object_id].hide()
                    self.marker_labels[object_id].deleteLater()
                    del self.marker_labels[object_id]
                    
                # 위험도 게이지바 제거
                if object_id in self.risk_labels:
                    self.risk_labels[object_id].hide()
                    self.risk_labels[object_id].deleteLater()
                    del self.risk_labels[object_id]
                    
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
            
            # 위험도 게이지바도 함께 제거
            for risk_widget in self.risk_labels.values():
                risk_widget.hide()
                risk_widget.deleteLater()
            self.risk_labels.clear()
            
            self.selected_marker_id = None
            logger.debug("모든 마커 제거 완료")
        except Exception as e:
            logger.error(f"마커 제거 실패: {str(e)}")
            
    def update_marker_positions(self):
        """모든 마커 위치 업데이트 (위젯 크기 변경 시)"""
        for marker in self.markers.values():
            x, y = self.calculate_marker_position(marker.data.x, marker.data.y, marker.data.size)
            if not marker.is_animating:
                marker.move(x, y)
            
            # 라벨도 같이 이동 (경계 제약 적용)
            label = self.marker_labels.get(marker.data.object_id)
            if label:
                marker_half_size = marker.data.size // 2
                label_x = x + marker_half_size - label.width()//2  # 마커 중앙에서 라벨 중앙 정렬
                label_y = y - label.height() - 2     # 마커 상단에서 2px 위
                
                # 라벨도 경계 제약 적용
                label_x = self._constrain_position(label_x, 0, self.width() - label.width())
                label_y = self._constrain_position(label_y, 0, self.height() - label.height())
                
                label.move(label_x, label_y)
                
            # 위험도 게이지바도 같이 이동 (경계 제약 적용)
            risk_widget = self.risk_labels.get(marker.data.object_id)
            if risk_widget:
                marker_half_size = marker.data.size // 2
                label = self.marker_labels.get(marker.data.object_id)
                if label:
                    label_y = label.y()
                    risk_x = x + marker_half_size - risk_widget.width()//2
                    risk_y = label_y - risk_widget.height() - 2
                    
                    # 위험도 게이지바도 경계 제약 적용
                    risk_x = self._constrain_position(risk_x, 0, self.width() - risk_widget.width())
                    risk_y = self._constrain_position(risk_y, 0, self.height() - risk_widget.height())
                    
                    risk_widget.move(risk_x, risk_y)
                
    def resizeEvent(self, event):
        """위젯 크기 변경 시 처리"""
        super().resizeEvent(event)
        self.update_marker_positions() 