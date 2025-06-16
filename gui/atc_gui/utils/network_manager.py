from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage
from models.detected_object import DetectedObject
from config import BirdRiskLevel, RunwayRiskLevel
from utils.tcp_client import TcpClient
from utils.udp_client import UdpClient
from utils.logger import logger
from config.settings import Settings
import cv2

class NetworkManager(QObject):
    """TCP 및 UDP 통신을 총괄하는 네트워크 관리자"""

    # UI가 연결할 시그널들
    object_detected = pyqtSignal(DetectedObject)
    bird_risk_changed = pyqtSignal(BirdRiskLevel)
    runway_a_risk_changed = pyqtSignal(RunwayRiskLevel)
    runway_b_risk_changed = pyqtSignal(RunwayRiskLevel)
    object_detail_response = pyqtSignal(DetectedObject)
    object_detail_error = pyqtSignal(str)
    frame_a_received = pyqtSignal(QImage, int)  # (프레임, 이미지ID)
    frame_b_received = pyqtSignal(QImage, int)  # (프레임, 이미지ID)
    tcp_connection_status_changed = pyqtSignal(bool, str)
    udp_connection_status_changed = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings.get_instance()
        self.tcp_client = TcpClient()
        self.udp_client = UdpClient()
        self._connect_signals()
        
        # 재연결 관련 설정
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)
        self.reconnect_interval = 3000  # 3초 간격으로 재연결 시도

    def _connect_signals(self):
        """내부 클라이언트의 시그널을 NetworkManager의 시그널로 전달"""
        # TCP 클라이언트 시그널 연결
        self.tcp_client.object_detected.connect(self._handle_object_detected)
        self.tcp_client.bird_risk_changed.connect(self.bird_risk_changed)
        self.tcp_client.runway_a_risk_changed.connect(self.runway_a_risk_changed)
        self.tcp_client.runway_b_risk_changed.connect(self.runway_b_risk_changed)
        self.tcp_client.object_detail_response.connect(self.object_detail_response)
        self.tcp_client.object_detail_error.connect(self.object_detail_error)
        self.tcp_client.map_response.connect(self._handle_map_response)
        self.tcp_client.cctv_a_response.connect(self._handle_cctv_a_response)
        self.tcp_client.cctv_b_response.connect(self._handle_cctv_b_response)

        # TCP 연결 상태 시그널 연결
        self.tcp_client.connected.connect(self._on_tcp_connected)
        self.tcp_client.disconnected.connect(self._on_tcp_disconnected)
        self.tcp_client.connection_error.connect(self._on_tcp_connection_error)

        # UDP 클라이언트 시그널 연결
        self.udp_client.frame_received.connect(self._handle_udp_frame)
        self.udp_client.connection_status_changed.connect(self.udp_connection_status_changed)

    def start_services(self):
        """네트워크 서비스 시작"""
        logger.info("네트워크 서비스 시작")
        self.tcp_client.connect_to_server()

    def stop_services(self):
        """네트워크 서비스 중지"""
        logger.info("네트워크 서비스 중지")
        self.tcp_client.disconnect_from_server()
        self.udp_client.disconnect()
        self.reconnect_timer.stop()

    def _attempt_reconnect(self):
        """TCP 재연결 시도"""
        # TCP 클라이언트 재연결 시도
        if self.tcp_client.connect_to_server():
            self.reconnect_timer.stop()
            self.tcp_connection_status_changed.emit(True, "TCP 서버에 재연결됨")
        else:
            self.reconnect_timer.start(self.reconnect_interval)
            self.tcp_connection_status_changed.emit(False, "서버 연결 실패: 3초 후 재시도합니다.")

    def _on_tcp_connected(self):
        """TCP 연결 성공 시 상태 전파"""
        self.tcp_connection_status_changed.emit(True, "TCP 서버에 연결되었습니다.")
        self.reconnect_timer.stop()

    def _on_tcp_disconnected(self):
        """TCP 연결 해제 시 상태 전파 및 재연결 시도"""
        self.tcp_connection_status_changed.emit(False, "TCP 서버 연결이 해제되었습니다.")
        self.reconnect_timer.start(self.reconnect_interval)

    def _on_tcp_connection_error(self, error_msg: str):
        """TCP 연결 오류 시 상태 전파 및 재연결 시도"""
        self.tcp_connection_status_changed.emit(False, f"TCP 연결 오류: {error_msg}")
        self.reconnect_timer.start(self.reconnect_interval)

    def _handle_object_detected(self, objects: list):
        """객체 감지 이벤트를 개별 객체로 처리"""
        for obj in objects:
            self.object_detected.emit(obj)

    def _handle_map_response(self, response: str):
        """지도 응답 처리"""
        if response.startswith("OK"):
            logger.info("지도 응답 수신 성공")
        else:
            logger.error(f"지도 응답 오류: {response}")

    def _handle_cctv_a_response(self, response: str):
        """CCTV A 응답 처리"""
        if response == "OK":
            logger.info("CCTV A 요청 승인됨")
            if not self.udp_client.is_connected():
                host = self.settings.server.tcp_ip
                port = self.settings.server.udp_port
                self.udp_client.connect(host, port)
        else:
            logger.error(f"CCTV A 요청 거부됨: {response}")

    def _handle_cctv_b_response(self, response: str):
        """CCTV B 응답 처리"""
        if response == "OK":
            logger.info("CCTV B 요청 승인됨")
            if not self.udp_client.is_connected():
                host = self.settings.server.tcp_ip
                port = self.settings.server.udp_port
                self.udp_client.connect(host, port)
        else:
            logger.error(f"CCTV B 요청 거부됨: {response}")

    def _handle_udp_frame(self, cam_id: str, frame, image_id: int = None):
        """UDP로 수신된 프레임을 카메라 ID에 따라 처리"""
        try:
            # OpenCV BGR -> RGB 변환
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # QImage로 변환
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # 카메라 ID에 따라 적절한 시그널 발생
            if cam_id == 'A':
                self.frame_a_received.emit(q_image, image_id)
            elif cam_id == 'B':
                self.frame_b_received.emit(q_image, image_id)
            else:
                logger.warning(f"알 수 없는 카메라 ID: {cam_id}")
                
        except Exception as e:
            logger.error(f"프레임 처리 중 오류 발생: {str(e)}")

    def request_cctv_a(self):
        """CCTV A 영상 요청"""
        logger.info("CCTV A 영상 요청")
        self.tcp_client.request_cctv_a()

    def request_cctv_b(self):
        """CCTV B 영상 요청"""
        logger.info("CCTV B 영상 요청")
        self.tcp_client.request_cctv_b()

    def request_object_detail(self, object_id: int):
        self.tcp_client.request_object_detail(object_id)

    def request_map(self):
        """지도 요청"""
        self.tcp_client.request_map() 