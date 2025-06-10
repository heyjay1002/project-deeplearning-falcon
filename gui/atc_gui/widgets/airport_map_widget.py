from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt

class AirportMapWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.map_item = None
        self.marker_items = []

    def set_map_image(self, image_path):
        pixmap = QPixmap(image_path)
        if self.map_item:
            self.scene.removeItem(self.map_item)
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        self.setSceneRect(self.map_item.boundingRect())

    def add_marker(self, x, y, icon_path, row_idx, callback, icon_size=64):
        marker_pixmap = QPixmap(icon_path)
        marker_pixmap = marker_pixmap.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        marker_item = QGraphicsPixmapItem(marker_pixmap)
        marker_item.setOffset(x, y)
        marker_item.setData(0, row_idx)  # row 인덱스 저장
        marker_item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        self.scene.addItem(marker_item)
        self.marker_items.append(marker_item)
        # 클릭 이벤트 연결
        def mousePressEvent(event, idx=row_idx):
            callback(idx)
        marker_item.mousePressEvent = mousePressEvent

    def clear_markers(self):
        for marker in self.marker_items:
            self.scene.removeItem(marker)
        self.marker_items.clear() 