"""
UDP 클라이언트 모듈
"""

import socket
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import time
import threading
import logging
from collections import deque
from PyQt6.QtNetwork import QUdpSocket
from config.settings import Settings

logger = logging.getLogger(__name__)

class UdpClient(QObject):
    """UDP 클라이언트 클래스"""
    
    # 시그널 정의
    frame_received = pyqtSignal(str, np.ndarray, int)  # (카메라 ID, 프레임, 이미지ID)
    connection_status_changed = pyqtSignal(bool, str)  # (연결 상태, 메시지)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings.get_instance()
        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._receive_frames)
        
        # 연결 상태 및 에러 처리 변수
        self.is_connected = False
        self.current_camera = None  # 현재 연결된 카메라 ID
        
        # 프레임 처리 관련 변수
        self.frame_buffer = {'A': deque(maxlen=5), 'B': deque(maxlen=5)}
        self.max_fps = 30
        self.last_frame_time = {'A': 0, 'B': 0}
        self.frame_interval = 1.0 / self.max_fps
        
        # 에러 처리 관련 변수
        self.retry_delay = 1.0
        self.max_retry_delay = 30.0
        self.retry_timer = QTimer(self)
        self.retry_timer.timeout.connect(self._attempt_reconnect)
        
        # 초기 연결 상태는 연결되지 않음으로 설정
        self.connection_status_changed.emit(False, "초기화됨")
        
        logger.info("UDP 클라이언트 초기화 완료")

    def set_max_fps(self, fps: int):
        """최대 FPS 설정"""
        self.max_fps = max(1, min(60, fps))
        self.frame_interval = 1.0 / self.max_fps
        logger.info(f"최대 FPS 설정: {self.max_fps}")

    def _should_process_frame(self) -> bool:
        """현재 프레임을 처리해야 하는지 결정"""
        current_time = time.time()
        if not self.frame_times or (current_time - self.last_frame_time) >= self.frame_interval:
            self.last_frame_time = current_time
            self.frame_times.append(current_time)
            return True
        return False

    def _emit_connection_status(self, is_connected, message):
        if self._last_connection_status != is_connected:
            self.connection_status_changed.emit(is_connected, message)
            logger.info(f"UDP 연결 상태 변경: {message}")
            self._last_connection_status = is_connected

    def connect_to_camera(self, camera_id: str) -> bool:
        """특정 카메라에 연결"""
        try:
            if self.current_camera == camera_id and self.is_connected:
                logger.info(f"이미 카메라 {camera_id}에 연결되어 있음")
                return True
                
            # 이전 연결이 있다면 해제
            if self.socket.state() != QUdpSocket.SocketState.UnconnectedState:
                self.socket.close()
                
            # 새로운 연결 시도
            self.socket.bind()
            self.is_connected = True
            self.current_camera = camera_id
            self.connection_status_changed.emit(True, f"카메라 {camera_id} 연결됨")
            logger.info(f"카메라 {camera_id} 연결 성공")
            return True
            
        except Exception as e:
            logger.error(f"카메라 {camera_id} 연결 실패: {str(e)}")
            self.is_connected = False
            self.current_camera = None
            self.connection_status_changed.emit(False, f"카메라 {camera_id} 연결 실패")
            return False

    def disconnect(self):
        """연결 해제"""
        try:
            if self.socket:
                self.socket.close()
            self.is_connected = False
            self.current_camera = None
            self.connection_status_changed.emit(False, "연결 해제됨")
            logger.info("UDP 연결 해제")
        except Exception as e:
            logger.error(f"연결 해제 중 오류: {str(e)}")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected and self.socket is not None

    def _receive_frames(self) -> None:
        """프레임 수신 스레드"""
        logger.info("UDP 프레임 수신 스레드 시작")
        
        frame_count = 0
        last_log_time = time.time()
        last_frame_time = 0
        target_fps = 10
        frame_interval = 1.0 / target_fps
        
        while self.is_running and self.socket:
            try:
                data, addr = self.socket.recvfrom(65536)
                
                current_time = time.time()
                if current_time - last_frame_time < frame_interval:
                    continue
                    
                frame_count += 1
                
                if current_time - last_log_time >= 1.0:
                    logger.debug(f"UDP 데이터 수신: {frame_count} FPS")
                    frame_count = 0
                    last_log_time = current_time
                
                if self._last_connection_status is not True:
                    self._emit_connection_status(True, f"UDP 영상 수신 중 ({self.server_address})")
                
                try:
                    first_colon = data.find(b':')
                    if first_colon == -1:
                        continue
                    
                    cam_id = data[:first_colon].decode()
                    
                    second_colon = data.find(b':', first_colon + 1)
                    
                    if second_colon == -1:
                        frame_data = data[first_colon+1:]
                        img_id = None
                    else:
                        try:
                            img_id = int(data[first_colon+1:second_colon])
                            frame_data = data[second_colon+1:]
                        except ValueError:
                            frame_data = data[first_colon+1:]
                            img_id = None
                    
                    frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # 버퍼가 가득 찼을 때 가장 오래된 프레임 제거
                        if len(self.frame_buffer[cam_id]) >= self.frame_buffer[cam_id].maxlen:
                            self.frame_buffer[cam_id].popleft()
                            
                        self.frame_buffer[cam_id].append((frame, img_id))
                        
                        # 버퍼가 충분히 찼을 때만 프레임 전송
                        if len(self.frame_buffer[cam_id]) >= 2:
                            frame, img_id = self.frame_buffer[cam_id].popleft()
                            self.frame_received.emit(cam_id, frame, img_id)
                            
                        last_frame_time = current_time
                        
                except Exception as e:
                    logger.error(f"프레임 처리 중 오류: {str(e)}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"프레임 수신 중 오류 발생: {str(e)}")
                    time.sleep(min(self.retry_delay, self.max_retry_delay))
                    self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
        
        logger.info("UDP 프레임 수신 스레드 종료")

    def cleanup(self):
        """UDP 클라이언트 정리"""
        self.disconnect()
        logger.info("UDP 클라이언트 정리 완료")

    def _attempt_reconnect(self):
        """재연결 시도"""
        try:
            if self.socket and self.socket.state() == QUdpSocket.SocketState.UnconnectedState:
                logger.info("UDP 재연결 시도")
                self.socket.bind()
                self.is_connected = True
                self.connection_status_changed.emit(True, "재연결됨")
                self.retry_timer.stop()
                self.retry_delay = 1.0  # 재연결 성공 시 딜레이 초기화
            else:
                # 재연결 실패 시 지수 백오프 적용
                self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
                logger.warning(f"UDP 재연결 실패. 다음 시도까지 {self.retry_delay}초 대기")
        except Exception as e:
            logger.error(f"UDP 재연결 시도 중 오류: {str(e)}")
            self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)

    def _handle_connection_error(self, error_msg: str):
        """연결 오류 처리"""
        logger.error(f"UDP 연결 오류: {error_msg}")
        self.is_connected = False
        self.connection_status_changed.emit(False, error_msg)
        
        # 재연결 타이머 시작
        if not self.retry_timer.isActive():
            self.retry_timer.start(int(self.retry_delay * 1000)) 