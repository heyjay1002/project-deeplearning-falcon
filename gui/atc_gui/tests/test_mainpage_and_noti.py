import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socket
import time
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from main import WindowClass
from utils.interface import MessageInterface, MessagePrefix, DetectedObject
from views.notification_dialog import NotificationDialog
from config.constants import ObjectType, AirportZone as Zone
import base64
from datetime import datetime

# 테스트 이벤트 서버 (TCP)
class TestEventServer(QThread):
    test_event_received = pyqtSignal(str, str)  # (prefix, payload)

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 50007))
        server.listen(1)
        while True:
            conn, addr = server.accept()
            data_buffer = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data_buffer += chunk
                # 메시지는 보통 한 번에 다 도착한다고 가정
                if chunk.endswith(b'\n') or not chunk:
                    break
            
            data = data_buffer.decode().strip()

            if ':' in data:
                prefix, payload = data.split(':', 1)
                
                if prefix == MessagePrefix.MC_OD.value:
                    try:
                        object_id = int(payload)
                        print(f"[서버] 객체 상세정보 요청 받음: ID {object_id}")
                        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'images', 'detection_sample_bird.png')
                        
                        try:
                            with open(image_path, "rb") as image_file:
                                image_data_b64 = base64.b64encode(image_file.read()).decode('utf-8')
                        except FileNotFoundError:
                            print(f"[서버 오류] 이미지 파일 없음: {image_path}")
                            image_data_b64 = ""

                        # 프로토콜 형식 수정: x, y 좌표 제거
                        response_payload = f"OK,{object_id},{ObjectType.BIRD.value},{Zone.RWY_A.value},{datetime.now().isoformat()},{image_data_b64}"
                        response_msg = f"{MessagePrefix.MR_OD.value}:{response_payload}\n"
                        conn.sendall(response_msg.encode())
                        print(f"[서버] 응답 보냄: {response_msg[:100]}...")
                    except Exception as e:
                        print(f"[서버 오류] 상세정보 응답 생성 실패: {e}")
                else:
                    self.test_event_received.emit(prefix, payload)
            
            # 클라이언트가 데이터를 모두 받을 시간을 주기 위해 짧은 지연 후 소켓을 닫음
            time.sleep(0.1)
            conn.close()

def send_test_event_raw(msg):
    try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 50007))
        s.sendall(f"{msg}\n".encode())

        # 서버로부터 응답을 받을 수도 있으므로, 수신 로직 추가
        response_buffer = b""
        s.settimeout(2.0) # 타임아웃 설정
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response_buffer += chunk
        except socket.timeout:
            # 타임아웃은 예상된 동작일 수 있음 (응답이 없는 경우)
            pass
        finally:
    s.close()
        
        # 응답이 있다면 처리
        if response_buffer:
            response_str = response_buffer.decode().strip()
            if ':' in response_str:
                prefix, payload = response_str.split(':', 1)
                QApplication.instance().test_server.test_event_received.emit(prefix, payload)

    except Exception as e:
        print(f"이벤트 전송 오류: {e}")

class TestControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        btn_obj = QPushButton("이상객체 감지 이벤트 보내기")
        btn_bird = QPushButton("조류 위험도 이벤트 보내기")
        btn_rwy_a = QPushButton("활주로A 위험도 이벤트 보내기")
        btn_rwy_b = QPushButton("활주로B 위험도 이벤트 보내기")
        layout.addWidget(btn_obj)
        layout.addWidget(btn_bird)
        layout.addWidget(btn_rwy_a)
        layout.addWidget(btn_rwy_b)
        self.setLayout(layout)

        btn_obj.clicked.connect(self.send_object)
        btn_bird.clicked.connect(self.send_bird)
        btn_rwy_a.clicked.connect(self.send_rwy_a)
        btn_rwy_b.clicked.connect(self.send_rwy_b)

    def send_object(self):
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'images', 'detection_sample_bird.png')
        try:
            with open(image_path, "rb") as image_file:
                image_data_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            print(f"[서버 오류] 이미지 파일 없음: {image_path}")
            image_data_b64 = ""
        
        msg = f"ME_OD:123,{ObjectType.BIRD.name},200.0,100.0,{Zone.RWY_A.value},{datetime.now().isoformat()},{image_data_b64}"
        send_test_event_raw(msg)

    def send_bird(self):
        msg = "ME_BR:1"  # MEDIUM
        send_test_event_raw(msg)

    def send_rwy_a(self):
        msg = "ME_RA:1"  # HIGH
        send_test_event_raw(msg)

    def send_rwy_b(self):
        msg = "ME_RB:1"  # HIGH
        send_test_event_raw(msg)

def handle_test_event(window, prefix, payload):
    try:
        if prefix == MessagePrefix.ME_OD.value:
            objects = MessageInterface.parse_object_detection_event(payload)
            for obj in objects:
                window.main_page.network_manager.object_detected.emit(obj)
        elif prefix == MessagePrefix.ME_BR.value:
            risk_level = MessageInterface.parse_bird_risk_level_event(payload)
            window.main_page.network_manager.bird_risk_changed.emit(risk_level)
        elif prefix == MessagePrefix.ME_RA.value:
            risk_level = MessageInterface.parse_runway_risk_level_event(payload)
            window.main_page.network_manager.runway_a_risk_changed.emit(risk_level)
        elif prefix == MessagePrefix.ME_RB.value:
            risk_level = MessageInterface.parse_runway_risk_level_event(payload)
            window.main_page.network_manager.runway_b_risk_changed.emit(risk_level)
        elif prefix == MessagePrefix.MR_OD.value:
            print(f"[테스트] 객체 상세보기 응답 수신: {payload[:100]}...")
            if payload.startswith("OK"):
                try:
                    # OK,{id},{type},{zone},{timestamp},{image_b64}
                    parts = payload.split(',', 5)
                    if len(parts) == 6:
                        _, obj_id, obj_type_str, zone_str, timestamp_str, image_b64 = parts
                        
                        image_data = base64.b64decode(image_b64)
                        
                        obj = DetectedObject(
                            object_id=int(obj_id),
                            object_type=ObjectType(obj_type_str),
                            x_coord=0.0, # 상세 정보에는 좌표가 없음
                            y_coord=0.0,
                            zone=Zone(zone_str),
                            timestamp=datetime.fromisoformat(timestamp_str),
                            extra_info=None,
                            image_data=image_data
                        )
                        window.main_page.network_manager.object_detail_response.emit(obj)
                        print(f"[테스트] 객체 상세보기 UI 업데이트 완료: ID {obj.object_id}")
                    else:
                        print(f"[테스트] 잘못된 응답 형식: {payload}")
                except Exception as e:
                    print(f"[테스트] 객체 상세보기 응답 파싱 오류: {e}")
            else:
                window.main_page.network_manager.object_detail_error.emit(payload)
    except Exception as e:
        print(f"[테스트 이벤트 핸들러 오류] {e}")

# monkey patch는 반드시 여기!
origin_show_notification_dialog = WindowClass.show_notification_dialog

def     debug_show_notification_dialog(self, dialog_type, data):
    print(f"[DEBUG] 알림 다이얼로그 호출됨: {dialog_type}, id={getattr(data, 'object_id', None)}, type={getattr(data, 'object_type', None)}")
    if not hasattr(self, '_test_dialogs'):
        self._test_dialogs = []
    dialog = NotificationDialog(dialog_type, data, self)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)  # 항상 맨 위에 표시
    self._test_dialogs.append(dialog)  # 참조 유지!
    dialog.show()

WindowClass.show_notification_dialog = debug_show_notification_dialog

# network_manager의 request_object_detail 메서드 모킹
def mock_request_object_detail(object_id):
    """테스트용 객체 상세보기 요청 - 가상 서버로 전송"""
    print(f"[테스트] 객체 상세보기 요청: ID {object_id}")
    msg = f"{MessagePrefix.MC_OD.value}:{object_id}"
    # 이 함수는 이제 응답을 직접 처리하지 않고, 서버로 보내기만 함
    send_test_event_raw(msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # TestEventServer 인스턴스를 애플리케이션에 저장하여 어디서든 접근 가능하게 함
    app.test_server = TestEventServer()
    
    window = WindowClass()

    # network_manager의 메서드를 모킹으로 교체
    # mock_request_object_detail이 self를 받지 않으므로 __get__ 없이 바로 할당
    window.main_page.network_manager.request_object_detail = mock_request_object_detail
    
    # 테스트 서버의 시그널을 핸들러에 연결
    app.test_server.test_event_received.connect(lambda p, pl: handle_test_event(window, p, pl))
    app.test_server.start()
    
    window.show()

    test_panel = TestControlPanel()
    test_panel.setWindowTitle("테스트 이벤트 전송 패널")
    test_panel.show()

    sys.exit(app.exec()) 