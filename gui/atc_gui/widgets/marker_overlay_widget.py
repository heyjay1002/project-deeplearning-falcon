from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class MarkerOverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.markers = []

    def add_marker(self, x, y, icon_path, row_idx, callback, icon_size=64):
        marker = QLabel(self)
        marker.setPixmap(QPixmap(icon_path).scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio))
        marker.move(x, y)
        marker.show()
        marker.mousePressEvent = lambda event, idx=row_idx: callback(idx)
        self.markers.append(marker)
        return marker

    def move_marker(self, marker_idx, new_x, new_y):
        if 0 <= marker_idx < len(self.markers):
            self.markers[marker_idx].move(new_x, new_y)

    def clear_markers(self):
        for marker in self.markers:
            marker.setParent(None)
        self.markers.clear()