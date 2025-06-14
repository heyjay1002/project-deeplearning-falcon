"""
UDP 클라이언트 모듈
"""

import socket
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
import time
import threading
import logging
from collections import deque

logger = logging.getLogger(__name__)

class UdpClient(QObject):
    """UDP 클라이언트 클래스"""
    
    # 시그널 정의
    frame_received = pyqtSignal(str, object, int)  # (카메라 ID, 프레임, 이미지ID)
    connection_status_changed = pyqtSignal(bool, str)  # (연결 상태, 메시지)
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.is_running = False
        self.receive_thread = None
        self._connected = False
        self.server_address = None
        self._last_connection_status = None  # 최근 연결 상태 저장
        
        # FPS 제한 관련 변수
        self.max_fps = 30  # 최대 FPS
        self.frame_times = deque(maxlen=30)  # 최근 30프레임의 시간 기록
        self.last_frame_time = 0  # 마지막 프레임 처리 시간
        self.frame_interval = 1.0 / self.max_fps  # 프레임 간 최소 간격

    def set_max_fps(self, fps: int):
        """최대 FPS 설정"""
        self.max_fps = max(1, min(60, fps))  # 1~60 FPS 범위로 제한
        self.frame_interval = 1.0 / self.max_fps
        logger.info(f"최대 FPS 설정: {self.max_fps}")

    def _should_process_frame(self) -> bool:
        """현재 프레임을 처리해야 하는지 결정"""
        current_time = time.time()
        
        # 첫 프레임이거나 충분한 시간이 지났으면 처리
        if not self.frame_times or (current_time - self.last_frame_time) >= self.frame_interval:
            self.last_frame_time = current_time
            self.frame_times.append(current_time)
            return True
            
        return False

    def _emit_connection_status(self, is_connected, message):
        # 상태가 바뀔 때만 emit 및 로그
        if self._last_connection_status != is_connected:
            self.connection_status_changed.emit(is_connected, message)
            logger.info(f"UDP 연결 상태 변경: {message}")
            self._last_connection_status = is_connected

    def connect(self, host: str, port: int):
        """UDP 서버에 연결"""
        try:
            if self.socket:
                self.disconnect()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.socket.settimeout(1.0)
            try:
                self.socket.bind(('0.0.0.0', port))
                self._emit_connection_status(True, f"UDP 서버에 연결됨 ({host}:{port})")
            except Exception as e:
                self._emit_connection_status(False, f"UDP 연결 실패: {str(e)}")
                return
            self.server_address = (host, port)
            self.is_running = True
            self.receive_thread = threading.Thread(target=self._receive_frames)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            self._connected = True
        except Exception as e:
            self._emit_connection_status(False, f"UDP 연결 실패: {str(e)}")
            if self.socket:
                self.socket.close()
                self.socket = None

    def disconnect(self):
        """UDP 서버 연결 해제"""
        self.is_running = False
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
            self.receive_thread = None
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self._connected = False
        self._emit_connection_status(False, "연결 종료됨")
        logger.info("UDP 서버 연결 해제")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected and self.socket is not None

    def _receive_frames(self) -> None:
        """프레임 수신 스레드"""
        logger.info("UDP 프레임 수신 스레드 시작")
        
        # FPS 제한 관련 변수
        frame_count = 0
        last_log_time = time.time()
        last_frame_time = 0
        target_fps = 10  # 목표 FPS
        frame_interval = 1.0 / target_fps
        
        while self.is_running and self.socket:
            try:
                # 데이터 수신
                data, addr = self.socket.recvfrom(65536)
                
                # 수신된 데이터 로깅
                logger.info(f"[UDP] 수신 데이터 크기: {len(data)} 바이트")
                logger.info(f"[UDP] 데이터 형식: {data[:100]}")  # 처음 100바이트만 로깅
                
                # FPS 제한 확인
                current_time = time.time()
                if current_time - last_frame_time < frame_interval:
                    continue
                    
                # 프레임 카운트 증가
                frame_count += 1
                
                # 1초마다 한 번만 로그 출력
                if current_time - last_log_time >= 1.0:
                    logger.debug(f"UDP 데이터 수신: {frame_count} FPS")
                    frame_count = 0
                    last_log_time = current_time
                
                # 프레임 정상 수신 시 연결 성공으로 갱신
                if self._last_connection_status is not True:
                    self._emit_connection_status(True, f"UDP 영상 수신 중 ({self.server_address})")
                
                # 헤더 파싱 (cam_id:frame_data 또는 cam_id:img_id:frame_data 형식)
                try:
                    # 첫 번째 콜론 찾기
                    first_colon = data.find(b':')
                    if first_colon == -1:
                        logger.warning("[UDP] 콜론을 찾을 수 없음")
                        continue
                    
                    # 카메라 ID 파싱
                    cam_id = data[:first_colon].decode()
                    logger.info(f"[UDP] 카메라 ID: {cam_id}")
                    
                    # 두 번째 콜론 찾기
                    second_colon = data.find(b':', first_colon + 1)
                    
                    if second_colon == -1:
                        # cam_id:frame_data 형식
                        logger.info("[UDP] 이미지ID 없음 (단순 형식)")
                        frame_data = data[first_colon+1:]
                    else:
                        # cam_id:img_id:frame_data 형식
                        try:
                            img_id = int(data[first_colon+1:second_colon])
                            logger.info(f"[UDP] 이미지ID 파싱 성공: {img_id}")
                            frame_data = data[second_colon+1:]
                        except ValueError:
                            # img_id가 숫자가 아닌 경우, 단순 형식으로 처리
                            logger.warning(f"[UDP] 이미지ID 파싱 실패: {data[first_colon+1:second_colon]}")
                            frame_data = data[first_colon+1:]
                    
                    # 프레임 디코딩
                    frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        self.frame_received.emit(cam_id, frame, img_id if 'img_id' in locals() else None)
                        last_frame_time = current_time
                        
                except Exception as e:
                    logger.error(f"프레임 처리 중 오류: {str(e)}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"프레임 수신 중 오류 발생: {str(e)}")
                time.sleep(0.1)  # 오류 발생 시 잠시 대기
        
        logger.info("UDP 프레임 수신 스레드 종료")

    def cleanup(self) -> None:
        """리소스 정리"""
        self.disconnect() 