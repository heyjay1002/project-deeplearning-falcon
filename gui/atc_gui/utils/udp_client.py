import socket
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage
import numpy as np
import cv2
from config.settings import Settings
from config.constants import Constants
from utils.logger import logger

class UdpClient(QObject):
    """UDP 클라이언트 클래스"""
    
    # 시그널 정의
    frame_a_received = pyqtSignal(QImage)  # CCTV A 프레임 수신 시그널
    frame_b_received = pyqtSignal(QImage)  # CCTV B 프레임 수신 시그널
    connected = pyqtSignal()  # UDP 연결 성공 시그널
    disconnected = pyqtSignal()  # UDP 연결 해제 시그널
    connection_error = pyqtSignal(str)  # UDP 연결 오류 시그널
    
    def __init__(self):
        super().__init__()
        self.settings = Settings.get_instance()
        self.socket = None
        self.is_running = False
        self.receive_thread = None
        self.is_connected = False  # 실제 데이터 수신 여부 추적
        
    def connect(self):
        """UDP 서버에 연결"""
        try:
            logger.info(f"UDP 서버 연결 시도: {self.settings.server.udp_ip}:{self.settings.server.udp_port}")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.settings.server.udp_port))
            self.is_running = True
            self.is_connected = False  # 아직 실제 연결은 확인되지 않음
            
            # 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self._receive_frames)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            logger.info(f"UDP 포트 바인딩 성공: {self.settings.server.udp_port} (데이터 수신 대기 중)")
            # connected 시그널은 실제 데이터를 받았을 때 발생
            return True
            
        except Exception as e:
            error_msg = f"UDP 연결 실패: {e}"
            logger.error(error_msg)
            self.connection_error.emit(error_msg)
            return False
    
    def disconnect(self):
        """UDP 서버 연결 해제"""
        self.is_running = False
        self.is_connected = False
        if self.socket:
            self.socket.close()
            self.socket = None
        logger.info(f"UDP 서버 연결 해제: {self.settings.server.udp_ip}:{self.settings.server.udp_port}")
        self.disconnected.emit()
    
    def _receive_frames(self):
        """프레임 수신 스레드"""
        while self.is_running:
            try:
                # UDP 데이터 수신
                data, addr = self.socket.recvfrom(self.settings.server.udp_buffer_size)
                
                # 첫 번째 데이터 수신 시 연결 성공으로 간주
                if not self.is_connected:
                    self.is_connected = True
                    logger.info(f"UDP 서버 연결 성공: 첫 데이터 수신 from {addr}")
                    self.connected.emit()
                
                # 카메라 ID와 이미지 데이터 분리
                parts = data.split(Constants.UDP_DATA_SEPARATOR.encode())
                if len(parts) != 2:
                    continue
                    
                camera_id, image_data = parts
                camera_id = camera_id.decode('utf-8')
                
                # 이미지 데이터 디코딩
                nparr = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # OpenCV BGR -> RGB 변환
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # QImage로 변환
                    height, width, channel = frame.shape
                    bytes_per_line = 3 * width
                    q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                    
                    # 카메라 ID에 따라 적절한 시그널 발생
                    if camera_id == 'A':
                        self.frame_a_received.emit(q_image)
                    elif camera_id == 'B':
                        self.frame_b_received.emit(q_image)
                    else:
                        logger.warning(f"알 수 없는 카메라 ID: {camera_id}")
                    
            except Exception as e:
                if self.is_running:  # 정상적인 종료가 아닌 경우에만 오류 로그
                    logger.error(f"프레임 수신 오류: {e}")
                continue 