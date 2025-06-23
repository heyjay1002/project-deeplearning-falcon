import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication
from widgets.map_marker_widget import MapMarkerWidget

@pytest.fixture(scope="module")
def app():
    app = QApplication(sys.argv)
    yield app

@pytest.fixture
def map_widget(app):
    widget = MapMarkerWidget()
    widget.set_map_size(960, 720)  # 원본 지도 크기
    widget.resize(960, 720)        # 위젯 크기(동일하게)
    return widget

def test_marker_position_top_left(map_widget):
    x, y = map_widget.calculate_marker_position(0, 0)
    # 마커 중앙 정렬 보정값(-12) 반영
    assert x == -12
    assert y == -12

def test_marker_position_center(map_widget):
    x, y = map_widget.calculate_marker_position(480, 360)
    assert x == 468  # 480 - 12
    assert y == 348  # 360 - 12

def test_marker_position_bottom_right(map_widget):
    x, y = map_widget.calculate_marker_position(960, 720)
    assert x == 948  # 960 - 12
    assert y == 708  # 720 - 12

if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)]) 