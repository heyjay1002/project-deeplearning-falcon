"""
개선된 UDP 클라이언트 모듈
"""

import socket
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtNetwork import QUdpSocket, QHostAddress
import time
import threading
import logging
from collections import deque
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from config.settings import Settings
from utils.interface import ErrorHandler, ConnectionState, ProcessedFrame

logger = logging.getLogger(__name__)


@dataclass
class FrameHeader:
    """프레임 헤더 정보"""
    camera_id: str
    image_id: Optional[int]
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
                return None
            
            # OpenCV로 디코딩
            frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return None
            
            # 프레임 캐시에 저장 (최근 3개만 유지)
            if camera_id not in self.frame_cache:
                self.frame_cache[camera_id] = deque(maxlen=3)
            
            self.frame_cache[camera_id].append(frame)
            
            return frame
            
        except Exception:
            return None
    
    def get_cached_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """캐시된 프레임 반환"""
        if camera_id in self.frame_cache and self.frame_cache[camera_id]:
            return self.frame_cache[camera_id][-1]
        return None


class FrameStabilizer:
    """프레임 안정화 클래스"""
    
    def __init__(self, buffer_size: int = 3):
        self.buffer_size = buffer_size
        self.frame_buffers = {}
        self.target_fps = 15
        self.frame_interval = 1.0 / self.target_fps
        self.last_frame_time = {}
        
    def should_process_frame(self, camera_id: str) -> bool:
        """프레임 처리 여부 결정"""
        current_time = time.time()
        
        if camera_id not in self.last_frame_time:
            self.last_frame_time[camera_id] = 0
        
        if current_time - self.last_frame_time[camera_id] >= self.frame_interval:
            self.last_frame_time[camera_id] = current_time
            return True
        
        return False
    
    def add_frame(self, camera_id: str, frame: np.ndarray, image_id: Optional[int]) -> bool:
        """프레임 버퍼에 추가"""
        if camera_id not in self.frame_buffers:
            self.frame_buffers[camera_id] = deque(maxlen=self.buffer_size)
        
        # 프레임 품질 체크
        if self._check_frame_quality(frame):
            self.frame_buffers[camera_id].append((frame, image_id, time.time()))
            return True
        
        return False
    
    def get_stable_frame(self, camera_id: str) -> Optional[Tuple[np.ndarray, Optional[int]]]:
        """안정화된 프레임 반환"""
        if camera_id not in self.frame_buffers or not self.frame_buffers[camera_id]:
            return None
        
        # 버퍼가 충분히 찼을 때만 프레임 반환
        if len(self.frame_buffers[camera_id]) >= self.buffer_size // 2:
            frame, image_id, _ = self.frame_buffers[camera_id].popleft()
            return frame, image_id
        
        return None
    
    def _check_frame_quality(self, frame: np.ndarray) -> bool:
        """프레임 품질 체크"""
        try:
            if frame is None or frame.size == 0:
                return False
            
            # 기본적인 품질 체크 (너무 어둡거나 밝지 않은지)
            mean_brightness = np.mean(frame)
            return 10 < mean_brightness < 245
            
        except Exception:
            return False


class OptimizedUdpClient(QObject):
    """최적화된 UDP 클라이언트 클래스"""
    
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
        self.frame_stabilizer = FrameStabilizer()
        
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

    def connect(self, host: str, port: int) -> bool:
        """UDP 연결"""
        try:
            # 이전 연결 정리
            if self._connected:
                self.disconnect()
            
            logger.info(f"UDP 연결 시도: {host}:{port}")
            
            # UDP 클라이언트는 로컬 포트에 바인딩하여 데이터 수신
            # 서버 포트와 다른 포트를 사용하여 충돌 방지
            local_port = port + 1000  # 서버 포트 + 1000
            if not self.socket.bind(QHostAddress.Any, local_port):
                if not self._connection_logged:
                    logger.error(f"UDP 소켓 바인딩 실패 (포트: {local_port})")
                self._connected = False
                self.connection_status_changed.emit(False, "소켓 바인딩 실패")
                return False
            
            self.server_address = host
            self.server_port = port
            self._connected = True
            self._connection_logged = True
            
            logger.info(f"UDP 클라이언트 바인딩 성공 (포트: {local_port}), 데이터 수신 대기 중...")
            
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
            self.frame_stabilizer.frame_buffers.clear()
            self.frame_processor.frame_cache.clear()
            
            self.connection_status_changed.emit(False, "연결 해제됨")
            
        except Exception:
            pass  # 연결 해제 오류는 로그 안함

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected and self.socket.state() != QUdpSocket.SocketState.UnconnectedState

    def set_max_fps(self, fps: int):
        """최대 FPS 설정"""
        self.max_fps = max(5, min(60, fps))
        self.frame_stabilizer.target_fps = min(self.max_fps, 15)
        self.frame_stabilizer.frame_interval = 1.0 / self.frame_stabilizer.target_fps

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            **self.stats,
            'is_connected': self.is_connected(),
            'max_fps': self.max_fps,
            'buffer_sizes': {cam: len(buf) for cam, buf in self.frame_stabilizer.frame_buffers.items()}
        }

    def _on_data_ready(self):
        """데이터 수신 이벤트 처리"""
        try:
            while self.socket.hasPendingDatagrams():
                datagram_size = self.socket.pendingDatagramSize()
                data, host, port = self.socket.readDatagram(datagram_size)
                
                logger.info(f"UDP 데이터 수신: {len(data)} bytes from {host}:{port}")
                
                if data:
                    # 데이터 내용 일부 로그 (디버깅용)
                    if len(data) > 20:
                        logger.info(f"데이터 헤더: {data[:20]}")
                    else:
                        logger.info(f"전체 데이터: {data}")
                    
                    self._process_received_data(data)
                    
        except Exception as e:
            logger.error(f"UDP 데이터 수신 오류: {str(e)}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")

    def _process_received_data(self, data: bytes):
        """수신된 데이터 처리"""
        try:
            # 통계 업데이트
            self.stats['bytes_received'] += len(data)
            
            # 헤더 파싱
            header = self._parse_frame_header(data)
            if not header:
                return
            
            # 프레임 처리 여부 결정
            if not self.frame_stabilizer.should_process_frame(header.camera_id):
                self.stats['frames_dropped'] += 1
                return
            
            # 프레임 디코딩
            frame_data = data[header.data_offset:]
            frame = self.frame_processor.decode_frame(frame_data, header.camera_id)
            
            if frame is not None:
                self._handle_decoded_frame(header.camera_id, frame, header.image_id)
            
        except Exception:
            pass  # 데이터 처리 오류는 로그 안함

    def _parse_frame_header(self, data: bytes) -> Optional[FrameHeader]:
        """프레임 헤더 파싱"""
        try:
            # 첫 번째 콜론까지가 카메라 ID
            first_colon = data.find(b':')
            if first_colon == -1:
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
                    image_id = int(data[first_colon + 1:second_colon])
                    data_offset = second_colon + 1
                except ValueError:
                    # 이미지 ID 파싱 실패시 무시
                    image_id = None
                    data_offset = first_colon + 1
            
            return FrameHeader(
                camera_id=camera_id,
                image_id=image_id,
                timestamp=datetime.now(),
                frame_size=len(data) - data_offset,
                data_offset=data_offset
            )
            
        except Exception:
            return None

    def _handle_decoded_frame(self, camera_id: str, frame: np.ndarray, image_id: Optional[int]):
        """디코딩된 프레임 처리"""
        try:
            self.stats['frames_received'] += 1
            
            # 프레임 안정화 버퍼에 추가
            if self.frame_stabilizer.add_frame(camera_id, frame, image_id):
                # 안정화된 프레임 가져오기
                stable_frame_data = self.frame_stabilizer.get_stable_frame(camera_id)
                
                if stable_frame_data:
                    stable_frame, stable_image_id = stable_frame_data
                    
                    # 시그널 발생
                    self.frame_received.emit(camera_id, stable_frame, stable_image_id or 0)
                    
                    # 통계 업데이트
                    self.stats['frames_processed'] += 1
                    self._update_fps_stats(camera_id)
            
        except Exception:
            pass  # 프레임 처리 오류는 로그 안함

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
                'buffer_health': {},
                'overall_health': self._calculate_overall_health()
            }
            
            # 각 카메라별 성능 데이터
            for camera_id in self.current_fps.keys():
                # FPS 계산
                if camera_id in self.stats['fps_history'] and self.stats['fps_history'][camera_id]:
                    fps_values = list(self.stats['fps_history'][camera_id])
                    avg_fps = sum(fps_values) / len(fps_values)
                    performance_data['frames_per_sec'][camera_id] = avg_fps
                
                # 버퍼 상태
                buffer_size = len(self.frame_stabilizer.frame_buffers.get(camera_id, []))
                buffer_health = min(1.0, buffer_size / self.frame_stabilizer.buffer_size)
                performance_data['buffer_health'][camera_id] = buffer_health
            
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
                target_fps = self.frame_stabilizer.target_fps
                actual_fps = self.current_fps.get(camera_id, 0)
                fps_health = min(1.0, actual_fps / target_fps) if target_fps > 0 else 0.0
                
                # 버퍼 건강도
                buffer_size = len(self.frame_stabilizer.frame_buffers.get(camera_id, []))
                buffer_health = min(1.0, buffer_size / max(1, self.frame_stabilizer.buffer_size))
                
                # 전체 점수
                camera_health = (fps_health + buffer_health) / 2
                health_scores.append(camera_health)
            
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
            self.frame_stabilizer.frame_buffers.clear()
            self.frame_processor.frame_cache.clear()
            
        except Exception:
            pass  # 정리 중 오류는 로그 안함

    def get_frame_quality_info(self, camera_id: str) -> Dict[str, Any]:
        """프레임 품질 정보 반환"""
        try:
            cached_frame = self.frame_processor.get_cached_frame(camera_id)
            
            if cached_frame is None:
                return {'quality': 'unknown', 'details': 'No cached frame'}
            
            # 기본 품질 분석
            mean_brightness = np.mean(cached_frame)
            std_brightness = np.std(cached_frame)
            
            # 품질 점수 계산 (0-1)
            brightness_score = 1.0 - abs(mean_brightness - 127.5) / 127.5
            contrast_score = min(1.0, std_brightness / 50.0)
            overall_quality = (brightness_score + contrast_score) / 2
            
            return {
                'quality': 'good' if overall_quality > 0.7 else 'fair' if overall_quality > 0.4 else 'poor',
                'quality_score': overall_quality,
                'brightness': mean_brightness,
                'contrast': std_brightness,
                'resolution': f"{cached_frame.shape[1]}x{cached_frame.shape[0]}"
            }
            
        except Exception as e:
            return {'quality': 'error', 'details': str(e)}

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

# OptimizedUdpClient를 UdpClient로도 사용할 수 있도록 별칭 추가
UdpClient = OptimizedUdpClient