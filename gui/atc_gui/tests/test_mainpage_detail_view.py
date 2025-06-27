import pytest
from PyQt6.QtWidgets import QApplication, QPushButton, QTableWidgetItem
from views.main_page import MainPage
from utils.interface import DetectedObject, ObjectType, AirportArea, EventType
from datetime import datetime
import sys
from PyQt6.QtCore import QObject, pyqtSignal

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

@pytest.fixture
def main_page(app):
    # MainPage 인스턴스 생성
    page = MainPage()
    yield page


def test_detail_view_shows_object_info(main_page, qtbot):
    # 테스트용 버튼을 동적으로 추가
    def add_test_object():
        obj = DetectedObject(
            object_id=999,
            object_type=ObjectType.BIRD,
            x_coord=10.0,
            y_coord=20.0,
            area=AirportArea.GRASS_A,
            event_type=EventType.HAZARD,
            timestamp=datetime.now(),
            state_info=80,
            image_data=None
        )
        main_page.table_object_list.setRowCount(1)
        main_page.table_object_list.setItem(0, 0, QTableWidgetItem(str(obj.object_id)))
        main_page.table_object_list.setItem(0, 1, QTableWidgetItem(obj.area.value))
        main_page.table_object_list.setItem(0, 2, QTableWidgetItem(obj.object_type.value))
        main_page.object_detail_dialog.update_object_info(obj)
        main_page.object_area.setCurrentIndex(2)

    btn_test_data = QPushButton("테스트 데이터 추가", main_page)
    btn_test_data.move(10, 10)
    btn_test_data.clicked.connect(add_test_object)
    btn_test_data.show()

    # (이후 실제로 버튼을 클릭하거나, add_test_object()를 직접 호출해도 됨)
    # 예시: qtbot.mouseClick(btn_test_data, Qt.LeftButton)
    # 또는 add_test_object()

    # 아래는 실제로 상세정보가 잘 표시되는지 확인하는 코드
    add_test_object()
    detail_text = main_page.object_detail_dialog.detail_info.text()
    assert "ID: 999" in detail_text
    assert "종류: 조류" in detail_text or "종류: BIRD" in detail_text
    assert "위치: GRASS_A" in detail_text
    assert "상태 정보: 80" in detail_text
    assert main_page.object_detail_dialog.label_event_type.text() in ("위험", "HAZARD")

def add_test_object(main_page):
    obj = DetectedObject(
        object_id=999,
        object_type=ObjectType.BIRD,
        x_coord=10.0,
        y_coord=20.0,
        area=AirportArea.GRASS_A,
        event_type=EventType.HAZARD,
        timestamp=datetime.now(),
        state_info=80,
        image_data=None
    )
    main_page.table_object_list.setRowCount(1)
    main_page.table_object_list.setItem(0, 0, QTableWidgetItem(str(obj.object_id)))
    main_page.table_object_list.setItem(0, 1, QTableWidgetItem(obj.area.value))
    main_page.table_object_list.setItem(0, 2, QTableWidgetItem(obj.object_type.value))
    main_page.object_detail_dialog.update_object_info(obj)
    main_page.object_area.setCurrentIndex(2)

class DummyNetworkManager(QObject):
    first_object_detected = pyqtSignal(object)  # 누락된 시그널 추가
    object_detected = pyqtSignal(object)
    bird_risk_changed = pyqtSignal(object)
    runway_a_risk_changed = pyqtSignal(object)
    runway_b_risk_changed = pyqtSignal(object)
    object_detail_response = pyqtSignal(object)
    object_detail_error = pyqtSignal(str)
    frame_a_received = pyqtSignal(object, int)
    frame_b_received = pyqtSignal(object, int)
    tcp_connection_status_changed = pyqtSignal(bool, str)
    udp_connection_status_changed = pyqtSignal(bool, str)
    
    class DummyTcpClient(QObject):
        cctv_a_response = pyqtSignal(str)
        cctv_b_response = pyqtSignal(str)
        def __init__(self):
            super().__init__()
    
    def __init__(self):
        super().__init__()
        self.tcp_client = self.DummyTcpClient()
    
    def request_object_detail(self, object_id: int) -> bool:
        """객체 상세보기 요청 (더미 구현)"""
        # 테스트용 더미 응답 생성
        from utils.interface import DetectedObject, ObjectType, AirportArea, EventType
        from datetime import datetime
        
        obj = DetectedObject(
            object_id=object_id,
            object_type=ObjectType.BIRD,
            x_coord=10.0,
            y_coord=20.0,
            area=AirportArea.GRASS_A,
            event_type=EventType.HAZARD,
            timestamp=datetime.now(),
            state_info=80,
            image_data=None
        )
        
        # 시그널 발생
        self.object_detail_response.emit(obj)
        return True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_page = MainPage(network_manager=DummyNetworkManager())
    main_page.show()

    btn_test_data = QPushButton("테스트 데이터 추가", main_page)
    btn_test_data.move(10, 10)
    btn_test_data.clicked.connect(lambda: add_test_object(main_page))
    btn_test_data.show()

    sys.exit(app.exec()) 