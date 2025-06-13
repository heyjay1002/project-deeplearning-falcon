"""
Admin GUI 테스트 프로그램
메인 서버로부터 TCP 통신으로 검출 결과를 수신하고 표시
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import time
import socket
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from network.tcp import TCPClient
from config import *

class TCPReceiver(QThread):
    """TCP 통신을 담당하는 스레드"""
    message_received = pyqtSignal(str)  # 메시지 수신 시그널
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.client = TCPClient(host=DEFAULT_HOST, port=TCP_PORT_ADMIN)
    
    def run(self):
        """메인 실행 루프"""
        if not self.client.start():
            print("[ERROR] 서버 연결 실패")
            return
        
        print("[INFO] 서버 연결 성공")
        
        while self.running:
            try:
                # 바이너리 데이터 수신
                data = self.client.receive_binary()
                if data:
                    # 바이너리를 문자열로 변환
                    message = data.decode()
                    self.message_received.emit(message)
            except Exception as e:
                print(f"[ERROR] 데이터 수신 중 오류: {e}")
                time.sleep(0.001)
    
    def stop(self):
        """통신 중지"""
        self.running = False
        self.client.close()

class UDPVideoReceiver(QThread):
    frame_received = pyqtSignal(np.ndarray, str)  # (frame, cam_id)

    def __init__(self, port=4100):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.port))
        sock.settimeout(1.0)
        while self.running:
            try:
                data, _ = sock.recvfrom(65536)
                # 데이터 파싱: {cam_id}:{binary_img}
                sep_idx = data.find(b':')
                if sep_idx == -1:
                    continue
                cam_id = data[:sep_idx].decode()
                img_bytes = data[sep_idx+1:]
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame is not None:
                    print(f"[UDP] cam_id={cam_id}, frame_shape={frame.shape}")
                    self.frame_received.emit(frame, cam_id)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[UDP 수신 오류] {e}")

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    def __init__(self):
        super().__init__()
        self.initUI()
        self._init_tcp()
        self._init_udp()
    
    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle('Admin GUI Test')
        self.setGeometry(100, 100, 800, 600)
        
        # 메인 위젯과 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # 영상 표시 레이블
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # CCTV A 버튼
        self.cctv_a_button = QPushButton('CCTV A')
        self.cctv_a_button.clicked.connect(lambda: self._send_command('MC_CA\n'))
        button_layout.addWidget(self.cctv_a_button)
        
        # 지도 보기 버튼
        self.map_button = QPushButton('지도 보기')
        self.map_button.clicked.connect(lambda: self._send_command('MC_MP\n'))
        button_layout.addWidget(self.map_button)
        
        layout.addLayout(button_layout)
        
        # 상태 표시 레이블
        self.status_label = QLabel('상태: 서버 연결 대기 중...')
        layout.addWidget(self.status_label)
        
        # 명령어 메시지 레이블
        self.command_label = QLabel('명령어 메시지:')
        self.command_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        layout.addWidget(self.command_label)
        
        # 메시지 표시 영역
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        layout.addWidget(self.message_display)
    
    def _init_tcp(self):
        """TCP 통신 초기화"""
        self.tcp_receiver = TCPReceiver()
        self.tcp_receiver.message_received.connect(self._on_tcp_message)
        self.tcp_receiver.start()

    def _init_udp(self):
        """UDP 영상 수신 초기화"""
        self.udp_receiver = UDPVideoReceiver()
        self.udp_receiver.frame_received.connect(self._on_frame_received)
        self.udp_receiver.start()

    def _on_tcp_message(self, message: str):
        """TCP 메시지 수신 시 호출
        Args:
            message: 수신된 메시지
        """
        # 명령어 관련 메시지인 경우 command_label에 표시
        if message.startswith('MC_') or message.startswith('MR_'):
            self.command_label.setText(f'명령어 메시지: {message.strip()}')
        
        # 모든 메시지는 message_display에도 표시
        self.message_display.append(f"[수신] {message.strip()}")
    
    def _on_frame_received(self, frame, cam_id):
        """UDP로 영상 수신 시 호출"""
        # OpenCV BGR 이미지를 Qt QImage로 변환
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(scaled_pixmap)
        # 상태 표시
        self.status_label.setText(f'상태: 영상 수신(cam_id={cam_id})')

    def _send_command(self, command: str):
        """명령 전송
        Args:
            command: 전송할 명령 문자열
        """
        if hasattr(self, 'tcp_receiver') and self.tcp_receiver.client:
            try:
                self.tcp_receiver.client.send_message_binary(command.encode())
                self.message_display.append(f"[전송] {command.strip()}")
            except Exception as e:
                print(f"[ERROR] 명령 전송 실패: {e}")
                self.status_label.setText('상태: 명령 전송 실패')

    def closeEvent(self, event):
        """윈도우 종료 시 호출"""
        self.tcp_receiver.stop()
        if hasattr(self, 'udp_receiver'):
            self.udp_receiver.stop()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 