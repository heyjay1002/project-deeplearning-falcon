import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socket
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from main import WindowClass
from utils.interface import MessageInterface, MessagePrefix
from views.notification_dialog import NotificationDialog


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
            data = conn.recv(1024).decode()
            if ':' in data:
                prefix, payload = data.split(':', 1)
                self.test_event_received.emit(prefix, payload)
            conn.close()

def send_test_event_raw(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 50007))
    s.sendall(msg.encode())
    s.close()

class TestControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        btn_obj = QPushButton("객체 감지 이벤트 보내기")
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
        msg = "ME_OD:123,BIRD,100.0,200.0,RWY_A,2024-06-19T16:00:00"
        send_test_event_raw(msg)

    def send_bird(self):
        msg = "ME_BR:2"  # HIGH
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
    except Exception as e:
        print(f"[테스트 이벤트 핸들러 오류] {e}")

# monkey patch는 반드시 여기!
origin_show_notification_dialog = WindowClass.show_notification_dialog

def debug_show_notification_dialog(self, dialog_type, data):
    print(f"[DEBUG] 알림 다이얼로그 호출됨: {dialog_type}, {data}")
    if not hasattr(self, '_test_dialogs'):
        self._test_dialogs = []
    dialog = NotificationDialog(dialog_type, data, self)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)  # 항상 맨 위에 표시
    self._test_dialogs.append(dialog)  # 참조 유지!
    dialog.show()  # exec() 대신 show() 사용

WindowClass.show_notification_dialog = debug_show_notification_dialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowClass()
    window.show()

    test_server = TestEventServer()
    test_server.test_event_received.connect(lambda prefix, payload: handle_test_event(window, prefix, payload))
    test_server.start()

    test_panel = TestControlPanel()
    test_panel.setWindowTitle("테스트 이벤트 전송 패널")
    test_panel.show()

    sys.exit(app.exec()) 