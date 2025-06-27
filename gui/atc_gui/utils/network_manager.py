from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64

from config.constants import ObjectType, AirportArea, BirdRiskLevel, RunwayRiskLevel, EventType
from utils.interface import DetectedObject, ConnectionManager, ConnectionState, AccessControlSettings
from utils.tcp_client import TcpClient
from utils.udp_client import UdpClient
from utils.logger import logger
from config.settings import Settings

class NetworkManager(QObject):
    """네트워크 매니저 - 전체 네트워크 서비스 조율
    
    역할:
    - TCP/UDP 클라이언트 관리
    - 비즈니스 로직 처리 (CCTV 요청/응답)
    - UI와의 인터페이스
    - 연결 상태 통합 관리
    - 데이터 변환 및 전달
    """

    # UI가 연결할 시그널들
    object_detected = pyqtSignal(DetectedObject)
    first_object_detected = pyqtSignal(DetectedObject)  # 최초 감지 이벤트용
    bird_risk_changed = pyqtSignal(BirdRiskLevel)
    runway_a_risk_changed = pyqtSignal(RunwayRiskLevel)
    runway_b_risk_changed = pyqtSignal(RunwayRiskLevel)
    object_detail_response = pyqtSignal(DetectedObject)
    object_detail_error = pyqtSignal(str)
    frame_a_received = pyqtSignal(QImage, object)  # (프레임, 이미지ID)
    frame_b_received = pyqtSignal(QImage, object)  # (프레임, 이미지ID)
    tcp_connection_status_changed = pyqtSignal(bool, str)
    udp_connection_status_changed = pyqtSignal(bool, str)
    network_health_updated = pyqtSignal(dict)  # 네트워크 건강 상태
    
    # 출입 제어 시그널
    access_control_settings_received = pyqtSignal(AccessControlSettings)
    access_control_update_result = pyqtSignal(bool, str)  # (성공여부, 메시지)
    access_control_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings.get_instance()
        
        # 연결 관리자 및 메트릭
        self.connection_manager = ConnectionManager()
        
        # 클라이언트 초기화
        self.tcp_client = TcpClient()
        self.udp_client = UdpClient()
        
        # 시그널 연결
        self._connect_signals()
        
        # 상태 모니터링 타이머
        self.health_monitor_timer = QTimer(self)
        self.health_monitor_timer.timeout.connect(self._update_health_status)
        self.health_monitor_timer.start(5000)  # 5초마다 상태 체크

    def _connect_signals(self):
        """내부 클라이언트의 시그널을 NetworkManager의 시그널로 전달"""
        # TCP 클라이언트 시그널 연결
        self.tcp_client.object_detected.connect(self._handle_object_detected)
        self.tcp_client.first_object_detected.connect(self._handle_first_object_detected)  # 최초 감지 이벤트
        self.tcp_client.bird_risk_changed.connect(self.bird_risk_changed)
        self.tcp_client.runway_a_risk_changed.connect(self.runway_a_risk_changed)
        self.tcp_client.runway_b_risk_changed.connect(self.runway_b_risk_changed)
        self.tcp_client.object_detail_response.connect(self.object_detail_response)
        self.tcp_client.object_detail_error.connect(self.object_detail_error)
        self.tcp_client.map_response.connect(self._handle_map_response)
        self.tcp_client.cctv_a_response.connect(self._handle_cctv_a_response)
        self.tcp_client.cctv_b_response.connect(self._handle_cctv_b_response)
        self.tcp_client.cctv_frame_received.connect(self._handle_cctv_frame)

        # TCP 연결 상태 시그널 연결
        self.tcp_client.connected.connect(self._on_tcp_connected)
        self.tcp_client.disconnected.connect(self._on_tcp_disconnected)
        self.tcp_client.connection_error.connect(self._on_tcp_connection_error)
        
        # 출입 제어 시그널 연결
        self.tcp_client.access_control_response.connect(self.access_control_settings_received)
        self.tcp_client.access_control_update_response.connect(self.access_control_update_result)
        self.tcp_client.access_control_error.connect(self.access_control_error)

        # UDP 클라이언트 시그널 연결
        self.udp_client.frame_received.connect(self._handle_udp_frame)
        self.udp_client.connection_status_changed.connect(self._on_udp_status_changed)

    def start_services(self):
        """네트워크 서비스 시작"""
        try:
            # TCP 연결 시작
            self.connection_manager.set_tcp_state(ConnectionState.CONNECTING)
            self.tcp_client.connect_to_server()
                
        except Exception as e:
            logger.error(f"시스템 시작 실패: {e}")
            self.connection_manager.set_tcp_state(ConnectionState.ERROR)

    def stop_services(self):
        """네트워크 서비스 중지"""
        try:
            # 타이머 중지
            self.health_monitor_timer.stop()
            
            # 클라이언트 연결 해제
            self.tcp_client.disconnect_from_server()
            self.udp_client.disconnect()
            
            # 상태 업데이트
            self.connection_manager.set_tcp_state(ConnectionState.DISCONNECTED)
            self.connection_manager.set_udp_state(ConnectionState.DISCONNECTED)
            
        except Exception as e:
            logger.error(f"종료 중 오류: {e}")

    def _update_health_status(self):
        """네트워크 건강 상태 업데이트"""
        try:
            # 기본 상태만 전송
            health_report = self.connection_manager.get_overall_status()
            self.network_health_updated.emit(health_report)
            
        except Exception as e:
            logger.error(f"상태 업데이트 실패: {e}")

    # === TCP 이벤트 핸들러 ===
    def _on_tcp_connected(self):
        """TCP 연결 성공 시 상태 전파"""
        self.connection_manager.set_tcp_state(ConnectionState.CONNECTED)
        self.connection_manager.reset_reconnect_attempts()
        self.tcp_connection_status_changed.emit(True, "서버에 연결되었습니다.")

    def _on_tcp_disconnected(self):
        """TCP 연결 해제 시 상태 전파"""
        self.connection_manager.set_tcp_state(ConnectionState.DISCONNECTED)
        self.tcp_connection_status_changed.emit(False, "서버 연결이 해제되었습니다.")

    def _on_tcp_connection_error(self, error_msg: str):
        """TCP 연결 오류 시 상태 전파"""
        self.connection_manager.set_tcp_state(ConnectionState.ERROR)
        self.tcp_connection_status_changed.emit(False, f"연결 오류: {error_msg}")

    def _on_udp_status_changed(self, is_connected: bool, message: str):
        """UDP 상태 변경 처리"""
        if is_connected:
            self.connection_manager.set_udp_state(ConnectionState.CONNECTED)
        else:
            self.connection_manager.set_udp_state(ConnectionState.DISCONNECTED)
        
        self.udp_connection_status_changed.emit(is_connected, message)

    # === 메시지 핸들러 ===
    def _handle_object_detected(self, objects: List[DetectedObject]):
        """객체 감지 이벤트를 개별 객체로 처리"""
        try:
            for obj in objects:
                self._validate_and_emit_object(obj)
                
        except Exception as e:
            logger.error(f"객체 감지 처리 실패: {e}")

    def _handle_first_object_detected(self, objects: List[DetectedObject]):
        """최초 객체 감지 이벤트를 개별 객체로 처리 (알림용)"""
        try:
            for obj in objects:
                # 최초 감지 이벤트는 바로 알림 시그널 발생
                self.first_object_detected.emit(obj)
                logger.info(f"최초 객체 감지 알림: ID {obj.object_id} ({obj.object_type.value})")
                
        except Exception as e:
            logger.error(f"최초 객체 감지 처리 실패: {e}")

    def _validate_and_emit_object(self, obj_data):
        """객체 데이터 유효성 검증 후 시그널 발생"""
        try:
            # 이미 DetectedObject 인스턴스인 경우
            if isinstance(obj_data, DetectedObject):
                self.object_detected.emit(obj_data)
                return
            
            # 문자열 데이터인 경우 파싱
            if isinstance(obj_data, str):
                obj = self._parse_object_string(obj_data)
                if obj:
                    self.object_detected.emit(obj)
                    
        except Exception as e:
            logger.error(f"객체 데이터 처리 실패: {e}")

    def _parse_object_string(self, obj_data: str) -> Optional[DetectedObject]:
        """문자열 객체 데이터 파싱 (호환성 유지)"""
        try:
            fields = obj_data.split(',')
            if len(fields) < 5:
                return None

            # 기본 필드 파싱
            object_id = int(fields[0])
            object_type = ObjectType(fields[1])
            x_coord = float(fields[2])
            y_coord = float(fields[3])
            area = AirportArea(fields[4])
            
            # 선택적 필드 처리
            timestamp = datetime.now()
            state_info = None
            image_data = None
            
            # 나머지 필드 분석
            remaining_fields = fields[5:] if len(fields) > 5 else []
            
            for i, field in enumerate(remaining_fields):
                # 이미지 데이터 확인
                if field.startswith('data:image/'):
                    try:
                        if ',' in field:
                            _, base64_data = field.split(',', 1)
                            image_data = base64.b64decode(base64_data)
                    except Exception:
                        continue
                
                # 타임스탬프 확인
                elif 'T' in field or field.replace('.', '').isdigit():
                    try:
                        if 'T' in field:
                            timestamp = datetime.fromisoformat(field)
                        else:
                            timestamp = datetime.fromtimestamp(float(field))
                    except ValueError:
                        state_info = field
                
                # 기타 정보
                else:
                    state_info = field

            return DetectedObject(
                object_id=object_id,
                object_type=object_type,
                x_coord=x_coord,
                y_coord=y_coord,
                area=area,
                event_type=EventType.HAZARD,  # 기본값
                timestamp=timestamp,
                state_info=state_info,
                image_data=image_data
            )
            
        except Exception:
            return None

    def _handle_udp_frame(self, camera_id: str, frame, image_id: object):
        """UDP 프레임 처리 - 데이터 변환 및 전달만 담당"""
        try:
            if frame is None:
                logger.error(f"프레임이 None: 카메라 {camera_id}, 이미지 ID {image_id}")
                return
            
            # QImage로 변환
            qimage = self._convert_to_qimage(frame)
            
            if qimage:
                if camera_id == "A":
                    self.frame_a_received.emit(qimage, image_id or 0)
                elif camera_id == "B":
                    self.frame_b_received.emit(qimage, image_id or 0)
                else:
                    logger.warning(f"알 수 없는 카메라 ID: {camera_id}, 이미지 ID {image_id}")
            else:
                logger.error(f"QImage 변환 실패: 카메라 {camera_id}, 이미지 ID {image_id}")
                    
        except Exception as e:
            logger.error(f"프레임 처리 실패 (카메라 {camera_id}, 이미지 ID {image_id}): {e}")

    def _convert_to_qimage(self, frame) -> Optional[QImage]:
        """OpenCV 프레임을 QImage로 변환"""
        try:
            import cv2
            
            if frame is None or frame.size == 0:
                logger.error("프레임이 None이거나 크기가 0")
                return None
                
            # BGR을 RGB로 변환
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            qimage = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            result = qimage.copy()  # 복사본 반환
            
            return result
            
        except Exception as e:
            logger.error(f"이미지 변환 실패: {e}")
            return None

    def _handle_map_response(self, response: str):
        """지도 응답 처리"""
        pass  # 로그 없이 처리

    def _handle_cctv_a_response(self, response: str):
        """CCTV A 응답 처리 - 비즈니스 로직만 담당"""
        logger.info(f"CCTV A 응답 수신: {response}")
        if response == "OK":
            # UDP 연결 확인 및 연결
            if not self.udp_client.is_connected():
                self._ensure_udp_connection()
            else:
                pass
        else:
            logger.error(f"CCTV A 요청 거부됨: {response}")

    def _handle_cctv_b_response(self, response: str):
        """CCTV B 응답 처리 - 비즈니스 로직만 담당"""
        logger.info(f"CCTV B 응답 수신: {response}")
        if response == "OK":
            # UDP 연결 확인 및 연결
            if not self.udp_client.is_connected():
                self._ensure_udp_connection()
            else:
                pass
        else:
            logger.error(f"CCTV B 요청 거부됨: {response}")


    def _ensure_udp_connection(self):
        """UDP 연결 보장 - UDP 클라이언트에 위임"""
        host = self.settings.server.udp_ip
        port = self.settings.server.udp_port
        
        if not self.udp_client.connect(host, port):
            logger.error(f"UDP 연결 실패: {host}:{port}")
        else:
            pass

    def _handle_cctv_frame(self, camera_id: str, frame, image_id: object):
        """CCTV 프레임 처리 - TCP를 통한 프레임 처리"""
        try:
            # frame이 이미 QImage인 경우 직접 사용
            if hasattr(frame, 'size') and hasattr(frame, 'format'):
                # QImage 객체인 경우
                if camera_id == "A":
                    self.frame_a_received.emit(frame, image_id)
                elif camera_id == "B":
                    self.frame_b_received.emit(frame, image_id)
                else:
                    logger.warning(f"알 수 없는 카메라 ID: {camera_id}")
            else:
                # numpy array인 경우 QImage로 변환
                qimage = self._convert_to_qimage(frame)
                if qimage:
                    if camera_id == "A":
                        self.frame_a_received.emit(qimage, image_id)
                    elif camera_id == "B":
                        self.frame_b_received.emit(qimage, image_id)
                    else:
                        logger.warning(f"알 수 없는 카메라 ID: {camera_id}")
                else:
                    logger.warning("QImage 변환 실패")
                    
        except Exception as e:
            logger.error(f"프레임 처리 실패 ({camera_id}): {e}")

    # === 공개 인터페이스 메서드 ===
    def request_cctv_a(self):
        """CCTV A 영상 요청"""
        try:
            success = self.tcp_client.request_cctv_a()
            return success
            
        except Exception as e:
            logger.error(f"CCTV A 영상 요청 실패: {e}")
            return False

    def request_cctv_b(self):
        """CCTV B 영상 요청"""
        try:
            success = self.tcp_client.request_cctv_b()
            return success
            
        except Exception as e:
            logger.error(f"CCTV B 영상 요청 실패: {e}")
            return False

    def request_object_detail(self, object_id: int):
        """객체 상세보기 요청"""
        try:
            success = self.tcp_client.request_object_detail(object_id)

            logger.info(f"객체 상세보기 요청 결과: {success}")
            return success
            
        except Exception as e:
            logger.error(f"객체 상세보기 요청 실패: {e}")
            return False

    def request_map(self):
        """지도 요청"""
        try:
            success = self.tcp_client.request_map()
            return success
            
        except Exception as e:
            logger.error(f"지도 요청 실패: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 반환"""
        return self.connection_manager.get_overall_status()

    def set_udp_max_fps(self, fps: int):
        """UDP 최대 FPS 설정"""
        try:
            self.udp_client.set_max_fps(fps)
        except Exception:
            pass

    def request_access_control_settings(self):
        """출입 제어 설정 요청"""
        try:
            success = self.tcp_client.request_access_control_settings()
            return success
        except Exception as e:
            logger.error(f"출입 제어 설정 요청 실패: {e}")
            return False

    def update_access_control_settings(self, settings: AccessControlSettings):
        """출입 제어 설정 업데이트"""
        try:
            success = self.tcp_client.update_access_control_settings(settings)
            return success
        except Exception as e:
            logger.error(f"출입 제어 설정 업데이트 실패: {e}")
            return False

    def send_tcp_message(self, message: str):
        """TCP 메시지 전송"""
        try:
            success = self.tcp_client._send_message_direct(message, f"로그 요청: {message}")
            logger.info(f"TCP 메시지 전송: {message}")
            return success
        except Exception as e:
            logger.error(f"TCP 메시지 전송 실패: {e}")
            raise e