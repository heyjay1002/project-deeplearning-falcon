from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QLabel
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt
from typing import Callable, List, Dict, Optional

class MapMarkerWidget(QGraphicsView):
    """공항 지도 뷰 위젯 - 마커 오버레이 기능 포함"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 기본 설정
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 지도 이미지 아이템
        self.map_item = None
        
        # 마커 관리
        self.markers: List[Dict] = []
        self.marker_items: List[QGraphicsPixmapItem] = []
        self.default_icon_size = 64

    def set_map_image(self, image_path: str) -> None:
        """지도 이미지 설정"""
        pixmap = QPixmap(image_path)
        if self.map_item:
            self.scene.removeItem(self.map_item)
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        self.setSceneRect(self.map_item.boundingRect())

    def add_marker(self, x: float, y: float, icon_path: str, row_idx: int, 
                  callback: Callable, icon_size: int = None) -> QGraphicsPixmapItem:
        """마커 추가"""
        if icon_size is None:
            icon_size = self.default_icon_size
            
        # 마커 이미지 생성
        marker_pixmap = QPixmap(icon_path).scaled(
            icon_size, 
            icon_size, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 마커 아이템 생성
        marker_item = QGraphicsPixmapItem(marker_pixmap)
        marker_item.setOffset(x, y)
        marker_item.setData(0, row_idx)
        marker_item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        
        # 클릭 이벤트 연결
        def mousePressEvent(event, idx=row_idx):
            callback(idx)
        marker_item.mousePressEvent = mousePressEvent
        
        # 마커 정보 저장
        marker_info = {
            'item': marker_item,
            'position': (x, y),
            'row_idx': row_idx,
            'callback': callback,
            'icon_size': icon_size
        }
        
        self.markers.append(marker_info)
        self.marker_items.append(marker_item)
        self.scene.addItem(marker_item)
        
        return marker_item

    def move_marker(self, marker_idx: int, new_x: float, new_y: float) -> bool:
        """마커 이동"""
        if 0 <= marker_idx < len(self.markers):
            self.markers[marker_idx]['position'] = (new_x, new_y)
            self.marker_items[marker_idx].setOffset(new_x, new_y)
            return True
        return False

    def get_marker(self, marker_idx: int) -> Optional[Dict]:
        """마커 정보 조회"""
        if 0 <= marker_idx < len(self.markers):
            return self.markers[marker_idx]
        return None

    def clear_markers(self) -> None:
        """모든 마커 제거"""
        for item in self.marker_items:
            self.scene.removeItem(item)
        self.markers.clear()
        self.marker_items.clear()

    def set_icon_size(self, size: int) -> None:
        """기본 아이콘 크기 설정"""
        self.default_icon_size = size
        # 기존 마커들의 크기도 업데이트
        for marker in self.markers:
            item = marker['item']
            pixmap = item.pixmap()
            scaled_pixmap = pixmap.scaled(
                size, 
                size, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            item.setPixmap(scaled_pixmap)
            marker['icon_size'] = size

    def get_marker_count(self) -> int:
        """마커 개수 반환"""
        return len(self.markers)

    def resizeEvent(self, event) -> None:
        """위젯 크기 변경 이벤트"""
        super().resizeEvent(event)
        if self.map_item:
            # 지도 이미지가 위젯 크기에 맞게 조정되도록 함
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio) 