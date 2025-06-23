import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QUdpSocket, QHostAddress
import time
import logging
from collections import deque
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class FrameHeader:
    """프레임 헤더 정보"""
    camera_id: str
    image_id: int
    timestamp: datetime
    frame_size: int
    data_offset: int


class FrameProcessor:
    """프레임 처리 클래스"""
    
    def __init__(self):
        self.frame_cache = {}
        
    def decode_frame(self, frame_data: bytes, camera_id: str) -> Optional[np.ndarray]:
        """프레임 디코딩"""
        try:
            if not frame_data:
                logger.warning(f"프레임 데이터가 비어있음: 카메라 {camera_id}")
                return None
            
            # OpenCV로 디코딩
            frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.error(f"OpenCV 디코딩 실패: 카메라 {camera_id}")
                return None
            
            # 프레임 캐시에 저장 (최근 3개만 유지)
            if camera_id not in self.frame_cache:
                self.frame_cache[camera_id] = deque(maxlen=3)
            
            self.frame_cache[camera_id].append(frame)
            
            return frame
            
        except Exception as e:
            logger.error(f"프레임 디코딩 오류 (카메라 {camera_id}): {e}")
            return None
    
    def get_cached_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """캐시된 프레임 반환"""
        if camera_id in self.frame_cache and self.frame_cache[camera_id]:
            return self.frame_cache[camera_id][-1]
        return None


class UdpClient(QObject):
    """UDP 클라이언트 - 순수한 UDP 통신 담당
    
    역할:
    - UDP 소켓 관리
    - 데이터 수신 및 파싱
    - 프레임 처리
    - 연결 상태 관리
    - 성능 통계 수집
    """
    
    # 시그널 정의
    frame_received = pyqtSignal(str, np.ndarray, int)  # (카메라 ID, 프레임, 이미지ID)
    connection_status_changed = pyqtSignal(bool, str)  # (연결 상태, 메시지)
    performance_updated = pyqtSignal(dict)  # 성능 정보
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings.get_instance()
        
        # 네트워크 관련
        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._on_data_ready)
        self.socket.errorOccurred.connect(self._on_socket_error)
        
        # 연결 상태
        self._connected = False
        self.server_address = None
        self.server_port = None
        
        # 프레임 처리 관련
        self.frame_processor = FrameProcessor()
        
        # 성능 관련 설정
        self.max_fps = 15
        self.current_fps = {}
        
        # 통계
        self.stats = {
            'frames_received': 0,
            'frames_processed': 0,
            'frames_dropped': 0,
            'bytes_received': 0,
            'last_frame_time': {},
            'fps_history': {}
        }
        
        # 로그 상태 추적
        self._connection_logged = False
        
        # 타이머들
        self._setup_timers()
        
        # 연결 상태 초기화
        self.connection_status_changed.emit(False, "초기화됨")

    def _setup_timers(self):
        """타이머 설정"""
        # 성능 모니터링 타이머 (간격 늘림)
        self.performance_timer = QTimer(self)
        self.performance_timer.timeout.connect(self._update_performance_stats)
        self.performance_timer.start(5000)  # 5초마다
        
        # UDP 데이터 수신 상태 체크 타이머
        self.udp_check_timer = QTimer(self)
        self.udp_check_timer.timeout.connect(self._check_udp_data)
        self.udp_check_timer.start(3000)  # 3초마다

    def connect(self, host: str, port: int) -> bool:
        """UDP 연결 - PyQt6 호환성 개선"""
        try:
            # 이전 연결 정리
            if self._connected:
                self.disconnect()
            
            logger.info(f"UDP 연결 시도: {host}:{port}")
            logger.debug(f"현재 소켓 상태: {self.socket.state()}")
            
            # UDP 소켓을 지정된 포트에 바인드
            if not self.socket.bind(QHostAddress.SpecialAddress.Any, port):
                logger.error(f"UDP 소켓 바인드 실패: {self.socket.errorString()}")
                return False
            
            logger.info(f"UDP 소켓 바인드 성공: 포트 {port}")
            
            # 서버 정보 저장
            self.server_address = host
            self.server_port = port
            self._connected = True
            self._connection_logged = True
            
            logger.info(f"UDP 클라이언트 연결 성공, 데이터 수신 대기 중...")
            logger.debug(f"연결 후 소켓 상태: {self.socket.state()}")
            logger.debug(f"소켓이 데이터 수신 대기 중: {self.socket.isValid()}")
            logger.info(f"UDP 클라이언트가 포트 {self.socket.localPort()}에 바인딩됨")
            
            # 상태 업데이트
            self.connection_status_changed.emit(True, f"서버 {host}:{port} 연결됨")
            
            return True
            
        except Exception as e:
            if not self._connection_logged:
                logger.error(f"UDP 연결 실패: {str(e)}")
                self._connection_logged = True
            self._connected = False
            self.connection_status_changed.emit(False, f"연결 실패: {str(e)}")
            return False

    def disconnect(self):
        """연결 해제"""
        try:
            if self.socket.state() != QUdpSocket.SocketState.UnconnectedState:
                self.socket.close()
            
            self._connected = False
            self.server_address = None
            self.server_port = None
            self._connection_logged = False
            
            # 버퍼 정리
            self.frame_processor.frame_cache.clear()
            
            self.connection_status_changed.emit(False, "연결 해제됨")
            
        except Exception:
            pass  # 연결 해제 오류는 로그 안함

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        is_connected = self._connected and self.socket.state() != QUdpSocket.SocketState.UnconnectedState
        logger.debug(f"UDP 연결 상태 확인: _connected={self._connected}, socket_state={self.socket.state()}, is_valid={self.socket.isValid()}, result={is_connected}")
        return is_connected

    def set_max_fps(self, fps: int):
        """최대 FPS 설정"""
        self.max_fps = max(5, min(60, fps))

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            **self.stats,
            'is_connected': self.is_connected(),
            'max_fps': self.max_fps
        }

    def _on_data_ready(self):
        """데이터 수신 이벤트 처리"""
        try:
            datagram_count = 0
            total_bytes = 0
            
            while self.socket.hasPendingDatagrams():
                datagram_size = self.socket.pendingDatagramSize()
                data, host, port = self.socket.readDatagram(datagram_size)
                
                if data:
                    self._process_received_data(data)
                    datagram_count += 1
                    total_bytes += datagram_size
                    
            if datagram_count > 0:
                logger.info(f"UDP 데이터그램 처리: {datagram_count}개, {total_bytes}바이트")
                    
        except Exception as e:
            logger.error(f"UDP 데이터 수신 오류: {str(e)}")

    def _process_received_data(self, data: bytes):
        """수신된 데이터 처리 - 지연 없이 즉시 처리"""
        try:
            # 통계 업데이트
            self.stats['bytes_received'] += len(data)
            
            # 헤더 파싱
            header = self._parse_frame_header(data)
            if not header:
                logger.warning("프레임 헤더 파싱 실패")
                return
            
            logger.info(f"프레임 수신: 카메라 {header.camera_id}, 이미지 ID {header.image_id}")
            
            # 프레임 디코딩
            frame_data = data[header.data_offset:]
            frame = self.frame_processor.decode_frame(frame_data, header.camera_id)
            
            if frame is not None:
                # 즉시 시그널 발생 - 지연 없음
                self.frame_received.emit(header.camera_id, frame, header.image_id or 0)
                
                # 통계 업데이트
                self.stats['frames_received'] += 1
                self.stats['frames_processed'] += 1
                self._update_fps_stats(header.camera_id)
                
                logger.info(f"프레임 처리 완료: 카메라 {header.camera_id}, 이미지 ID {header.image_id}")
            else:
                self.stats['frames_dropped'] += 1
                logger.error(f"프레임 디코딩 실패: 카메라 {header.camera_id}, 이미지 ID {header.image_id}")
            
        except Exception as e:
            logger.error(f"데이터 처리 오류: {e}")

    def _parse_frame_header(self, data: bytes) -> Optional[FrameHeader]:
        """프레임 헤더 파싱"""
        try:
            # 첫 번째 콜론까지가 카메라 ID
            first_colon = data.find(b':')
            if first_colon == -1:
                logger.error("프레임 헤더 형식 오류: 첫 번째 콜론 없음")
                return None
            
            camera_id = data[:first_colon].decode('utf-8')
            
            # 두 번째 콜론까지가 이미지 ID (선택적)
            second_colon = data.find(b':', first_colon + 1)
            
            if second_colon == -1:
                # 이미지 ID가 없는 경우
                image_id = None
                data_offset = first_colon + 1
            else:
                # 이미지 ID가 있는 경우
                try:
                    image_id_str = data[first_colon + 1:second_colon].decode('utf-8')
                    image_id = int(image_id_str)
                    data_offset = second_colon + 1
                except ValueError:
                    # 이미지 ID 파싱 실패시 무시
                    image_id = None
                    data_offset = first_colon + 1
                except Exception as e:
                    image_id = None
                    data_offset = first_colon + 1
            
            frame_size = len(data) - data_offset
            
            header = FrameHeader(
                camera_id=camera_id,
                image_id=image_id,
                timestamp=datetime.now(),
                frame_size=frame_size,
                data_offset=data_offset
            )
            
            return header
            
        except Exception as e:
            logger.error(f"헤더 파싱 오류: {e}")
            return None

    def _update_fps_stats(self, camera_id: str):
        """FPS 통계 업데이트"""
        current_time = time.time()
        
        if camera_id not in self.stats['last_frame_time']:
            self.stats['last_frame_time'][camera_id] = current_time
            self.stats['fps_history'][camera_id] = deque(maxlen=30)
        
        # FPS 계산
        time_diff = current_time - self.stats['last_frame_time'][camera_id]
        if time_diff > 0:
            fps = 1.0 / time_diff
            self.stats['fps_history'][camera_id].append(fps)
            self.current_fps[camera_id] = fps
        
        self.stats['last_frame_time'][camera_id] = current_time

    def _update_performance_stats(self):
        """성능 통계 업데이트 (로그 없이)"""
        try:
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'frames_per_sec': {},
                'overall_health': self._calculate_overall_health()
            }
            
            # 각 카메라별 성능 데이터
            for camera_id in self.current_fps.keys():
                # FPS 계산
                if camera_id in self.stats['fps_history'] and self.stats['fps_history'][camera_id]:
                    fps_values = list(self.stats['fps_history'][camera_id])
                    avg_fps = sum(fps_values) / len(fps_values)
                    performance_data['frames_per_sec'][camera_id] = avg_fps
            
            self.performance_updated.emit(performance_data)
            
        except Exception:
            pass

    def _calculate_overall_health(self) -> float:
        """전체 건강 점수 계산"""
        try:
            if not self.current_fps:
                return 1.0 if self.is_connected() else 0.0
            
            health_scores = []
            
            for camera_id in self.current_fps.keys():
                # FPS 건강도 (목표 FPS 대비)
                target_fps = self.max_fps
                actual_fps = self.current_fps.get(camera_id, 0)
                fps_health = min(1.0, actual_fps / target_fps) if target_fps > 0 else 0.0
                health_scores.append(fps_health)
            
            return sum(health_scores) / len(health_scores) if health_scores else 0.0
            
        except Exception:
            return 0.0

    def _on_socket_error(self, error):
        """소켓 오류 처리 (로그 최소화)"""
        if not self._connection_logged:
            logger.error(f"UDP 소켓 오류: {self.socket.errorString()}")
            self._connection_logged = True
        
        self._connected = False
        self.connection_status_changed.emit(False, "UDP 소켓 오류")

    def cleanup(self):
        """UDP 클라이언트 정리"""
        try:
            # 타이머 중지
            self.performance_timer.stop()
            
            # 연결 해제
            self.disconnect()
            
            # 버퍼 정리
            self.frame_processor.frame_cache.clear()
            
        except Exception:
            pass  # 정리 중 오류는 로그 안함

    def force_reconnect(self):
        """강제 재연결"""
        try:
            if self.server_address and self.server_port:
                self.disconnect()
                time.sleep(1)  # 잠시 대기
                return self.connect(self.server_address, self.server_port)
            return False
            
        except Exception:
            return False

    def _check_udp_data(self):
        """UDP 데이터 수신 상태 체크"""
        if self._connected and self.socket.state() == QUdpSocket.SocketState.BoundState:
            logger.debug(f"UDP 상태 체크: 연결됨, 소켓상태={self.socket.state()}, 대기중데이터그램={self.socket.hasPendingDatagrams()}")
            if self.socket.hasPendingDatagrams():
                logger.info(f"대기 중인 UDP 데이터그램 발견: {self.socket.pendingDatagramSize()}바이트")
        else:
            logger.debug(f"UDP 상태 체크: 연결되지 않음 또는 바인딩되지 않음 (상태: {self.socket.state()})")