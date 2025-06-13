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
    connection_status_changed = pyqtSignal(bool, str)  # UDP 연결 상태 변경 시그널
    
    def __init__(self):
        super().__init__()
        self.settings = Settings.get_instance()
        self.socket = None
        self.is_running = False
        self.receive_thread = None
        self._is_connected = False  # 실제 데이터 수신 여부 추적
        
    def connect(self):
        """UDP 서버에 연결"""
        # 이미 연결되어 있는 경우 재연결하지 않음
        if self.socket is not None and self.is_running:
            logger.info("UDP 서버가 이미 연결되어 있습니다.")
            return

        try:
            # 기존 소켓이 있다면 정리
            if self.socket is not None:
                self.disconnect()

            # UDP 소켓 생성
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.settings.server.udp_buffer_size)
            
            # UDP 서버 주소
            server_address = (self.settings.server.udp_ip, self.settings.server.udp_port)
            logger.info(f"UDP 서버 연결 시도: {server_address[0]}:{server_address[1]}")
            
            # UDP는 연결이 필요 없으므로 바로 바인딩
            self.socket.bind(('0.0.0.0', 0))  # 임의의 포트에 바인딩
            logger.info(f"UDP 포트 바인딩 성공: {self.socket.getsockname()[1]}")
            
            # 서버 주소 설정
            self.server_address = server_address
            
            # 수신 스레드 시작
            self.is_running = True
            self.receive_thread = threading.Thread(target=self._receive_frames)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
        except Exception as e:
            error_msg = f"UDP 연결 오류: {e}"
            logger.error(error_msg)
            self.connection_error.emit(error_msg)
            self.disconnected.emit()
            if self.socket is not None:
                self.socket.close()
                self.socket = None
            self.is_running = False
            self._is_connected = False
    
    def disconnect(self):
        """UDP 서버 연결 해제"""
        self.is_running = False
        self._is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"UDP 소켓 종료 중 오류: {e}")
            finally:
                self.socket = None
        logger.info(f"UDP 서버 연결 해제: {self.settings.server.udp_ip}:{self.settings.server.udp_port}")
        self.disconnected.emit()
    
    def _receive_frames(self):
        """프레임 수신 스레드"""
        logger.info("UDP 프레임 수신 시작")
        while self.is_running:
            try:
                # UDP 데이터 수신
                data, addr = self.socket.recvfrom(self.settings.server.udp_buffer_size)
                
                # 첫 번째 데이터 수신 시 연결 성공으로 간주
                if not self._is_connected:
                    self._is_connected = True
                    logger.info(f"UDP 서버 연결 성공: {addr[0]}:{addr[1]}")
                    self.connected.emit()
                    self.connection_status_changed.emit(True, "UDP 서버에 연결되었습니다.")
                
                # 카메라 ID와 이미지 데이터 분리
                try:
                    # 첫 번째 ':' 찾기
                    sep = data.find(b':')
                    if sep == -1:
                        continue
                    
                    # 카메라 ID 추출
                    camera_id = data[:sep].decode('utf-8')
                    
                    # 이미지 데이터 추출 (이미지 ID가 있는 경우와 없는 경우 모두 처리)
                    image_data = data[sep + 1:]
                    if b':' in image_data:  # 이미지 ID가 있는 경우
                        img_id, image_data = image_data.split(b':', 1)
                    
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
                            
                except Exception as e:
                    logger.error(f"프레임 처리 오류: {e}")
                    continue
                    
            except Exception as e:
                if self.is_running:
                    logger.error(f"프레임 수신 오류: {e}")
                    self._is_connected = False
                    self.connection_status_changed.emit(False, f"UDP 연결 오류: {e}")
                continue
        logger.info("UDP 프레임 수신 종료")

    def stop_streaming(self):
        """UDP 스트리밍 중지"""
        self.is_running = False
        logger.info("UDP 스트리밍 중지됨")

    def start_streaming(self):
        """UDP 스트리밍 시작"""
        self.is_running = True
        logger.info("UDP 스트리밍 시작됨")

    def is_connected(self) -> bool:
        """UDP 연결 상태 확인"""
        return (self.socket is not None and 
                self.is_running and 
                self._is_connected and 
                self.receive_thread is not None and 
                self.receive_thread.is_alive()) 