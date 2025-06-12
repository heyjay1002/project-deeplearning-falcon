from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

class MapMarkerManager:
    def __init__(self, map_label, marker_callback=None):
        self.map_label = map_label  # 지도 QLabel
        self.marker_callback = marker_callback  # 마커 클릭 시 호출할 함수
        self.markers = []

    def clear_markers(self):
        for marker in self.markers:
            marker.setParent(None)
        self.markers.clear()

    def add_marker(self, x, y, row_idx, icon_path):
        marker = QPushButton(self.map_label)
        marker.setIcon(QIcon(icon_path))
        marker.setIconSize(QSize(32, 32))
        marker.setFlat(True)
        marker.setStyleSheet("background: transparent;")
        marker.move(x, y)
        marker.show()
        marker.clicked.connect(lambda: self.marker_callback(row_idx) if self.marker_callback else None)
        self.markers.append(marker) 