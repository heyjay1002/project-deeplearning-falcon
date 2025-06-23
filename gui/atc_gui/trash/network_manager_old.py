from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage
from models.detected_object import DetectedObject
from config.constants import ObjectType, AirportZone, BirdRiskLevel, RunwayRiskLevel
from utils.tcp_client import TcpClient
from gui.atc_gui.trash.udp_client_old2 import UdpClient
from utils.logger import logger
from config.settings import Settings
import cv2
from datetime import datetime
import base64

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
        self.reconnect_interval = self.settings.server.reconnect_interval * 1000  # 밀리초 단위로 변환

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
        # self.udp_client.frame_received.connect(self._handle_udp_frame)
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
        for obj_data in objects:
            try:
                # 객체 정보 파싱
                fields = obj_data.split(',')
                if len(fields) < 5:  # 최소 필수 필드 수 확인 (timestamp와 이미지 제외)
                    logger.error(f"잘못된 객체 데이터 형식: {obj_data}")
                    continue

                object_id = int(fields[0])
                object_type = ObjectType(fields[1])
                x_coord = float(fields[2])
                y_coord = float(fields[3])
                zone = AirportZone(fields[4])
                
                # timestamp와 extra_info, image_data 처리
                timestamp = None
                extra_info = None
                image_data = None
                
                # 필드 분석
                remaining_fields = fields[5:] if len(fields) > 5 else []
                
                # 이미지 데이터 찾기
                for i, field in enumerate(remaining_fields):
                    if field.startswith('data:image/'):
                        try:
                            # Base64 데이터 유효성 검사
                            if ',' not in field:
                                logger.warning("잘못된 이미지 데이터 형식: 콤마(,)가 없습니다.")
                                continue
                            
                            mime_type, base64_data = field.split(',', 1)
                            # Base64 디코딩 테스트
                            try:
                                base64.b64decode(base64_data)
                                image_data = field
                            except Exception as e:
                                logger.error(f"잘못된 Base64 이미지 데이터: {str(e)}")
                                continue
                            
                            # 이미지 데이터 이전의 필드들을 처리
                            if i > 0:
                                # 첫 번째 필드가 timestamp 형식인지 확인
                                try:
                                    timestamp = datetime.fromisoformat(remaining_fields[0])
                                    # 나머지 필드들은 extra_info
                                    if i > 1:
                                        extra_info = remaining_fields[1]
                                except ValueError:
                                    # timestamp가 아닌 경우 extra_info로 처리
                                    extra_info = remaining_fields[0]
                            break
                        except Exception as e:
                            logger.error(f"이미지 데이터 처리 중 오류 발생: {str(e)}")
                            continue
                else:
                    # 이미지 데이터가 없는 경우
                    if remaining_fields:
                        # 첫 번째 필드가 timestamp 형식인지 확인
                        try:
                            timestamp = datetime.fromisoformat(remaining_fields[0])
                            # 나머지 필드는 extra_info
                            if len(remaining_fields) > 1:
                                extra_info = remaining_fields[1]
                        except ValueError:
                            # timestamp가 아닌 경우 extra_info로 처리
                            extra_info = remaining_fields[0]

                # timestamp가 없는 경우 현재 시간 사용
                if timestamp is None:
                    timestamp = datetime.now()

                # DetectedObject 생성
                obj = DetectedObject(
                    object_id=object_id,
                    object_type=object_type,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    zone=zone,
                    timestamp=timestamp,
                    extra_info=extra_info,
                    image_data=image_data
                )
                
                self.object_detected.emit(obj)
                
            except Exception as e:
                logger.error(f"객체 데이터 처리 중 오류 발생: {str(e)}")
                continue

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
                host = self.settings.server.udp_ip
                port = self.settings.server.udp_port
                self.udp_client.connect(host, port)
        else:
            logger.error(f"CCTV A 요청 거부됨: {response}")

    def _handle_cctv_b_response(self, response: str):
        """CCTV B 응답 처리"""
        if response == "OK":
            logger.info("CCTV B 요청 승인됨")
            if not self.udp_client.is_connected():
                host = self.settings.server.udp_ip
                port = self.settings.server.udp_port
                self.udp_client.connect(host, port)
        else:
            logger.error(f"CCTV B 요청 거부됨: {response}")

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

    def _handle_udp_frame(self, frame: QImage, camera_id: int):
        # FPS는 UDP 클라이언트에서 계산된 값을 사용
        self.metrics.record_frame_stats(camera_id, frame.size().width() * frame.size().height(), self.settings.data.object_update_interval) 