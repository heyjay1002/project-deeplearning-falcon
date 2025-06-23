from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
import asyncio
from typing import Optional, Any, Callable
from datetime import datetime
import time

from config import Settings, Constants, MessagePrefix, BirdRiskLevel, RunwayRiskLevel
from utils.interface import (MessageInterface, MessageParser, 
                           DetectedObject)
from utils.logger import logger

class MessageQueue:
    """메시지 큐 관리 클래스"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = []
        self.max_size = max_size
        
    def enqueue(self, message: str, priority: int = 0):
        if len(self.queue) >= self.max_size:
            self.queue.pop(0)
        
        insert_pos = len(self.queue)
        for i, (_, msg_priority) in enumerate(self.queue):
            if priority > msg_priority:
                insert_pos = i
                break
        
        self.queue.insert(insert_pos, (message, priority))
    
    def dequeue(self) -> Optional[str]:
        if self.queue:
            message, _ = self.queue.pop(0)
            return message
        return None
    
    def clear(self):
        self.queue.clear()
    
    def size(self) -> int:
        return len(self.queue)


class TcpClient(QObject):
    """TCP 클라이언트"""
    
    # === 시그널 정의 ===
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    
    object_detected = pyqtSignal(list)
    first_object_detected = pyqtSignal(list)  # 최초 감지 이벤트용
    bird_risk_changed = pyqtSignal(BirdRiskLevel)
    runway_a_risk_changed = pyqtSignal(RunwayRiskLevel)
    runway_b_risk_changed = pyqtSignal(RunwayRiskLevel)
    
    cctv_a_response = pyqtSignal(str)
    cctv_b_response = pyqtSignal(str)
    map_response = pyqtSignal(str)
    object_detail_response = pyqtSignal(DetectedObject)
    object_detail_error = pyqtSignal(str)
    
    # CCTV 프레임 시그널 추가
    cctv_frame_received = pyqtSignal(str, object, int)  # (카메라 ID, QImage, 이미지ID)

    def __init__(self):
        super().__init__()
        
        # 설정 및 인터페이스
        self.settings = Settings.get_instance()
        self.message_interface = MessageInterface()
        
        self.message_queue = MessageQueue()
        
        # TCP 소켓 및 연결 관리
        self.socket = QTcpSocket(self)
        self._setup_socket_signals()
        
        # 타이머들
        self._setup_timers()
        
        # 상태 관리
        self.message_buffer = ""
        self.is_connecting = False
        self.connection_start_time = None
        
        # 재연결 관리
        self.reconnect_count = 0
        self.max_reconnect_attempts = None  # 무한 재시도
        self.reconnect_interval = 5000  # 5초
        
        # 로그 상태 추적 (중복 방지)
        self._initial_connection_attempted = False
        self._connection_successful = False
        
        # 통계
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connection_attempts': 0,
            'last_activity': time.time()
        }
        
        # CCTV 상태 추적
        self.active_cctv = None  # 현재 활성화된 CCTV ('A' 또는 'B')

    def _setup_timers(self):
        """타이머 설정"""
        # 연결 타임아웃 타이머
        self.connection_timeout_timer = QTimer(self)
        self.connection_timeout_timer.setSingleShot(True)
        self.connection_timeout_timer.timeout.connect(self._on_connection_timeout)
        
        # 재연결 타이머
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)
        
        # 메시지 처리 타이머
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self._process_message_queue)
        self.message_timer.start(100)  # 100ms마다

    def connect_to_server(self) -> bool:
        """서버에 연결 시도"""
        if self.is_connected():
            return True
            
        if self.is_connecting:
            return False
        
        try:
            self.is_connecting = True
            self.connection_start_time = time.time()
            self.stats['connection_attempts'] += 1
            
            # 첫 연결 시도만 로그 출력
            if not self._initial_connection_attempted:
                logger.info("TCP 연결 시도 중...")
                self._initial_connection_attempted = True
            
            # 이전 연결 정리
            self._cleanup_previous_connection()
            
            # 연결 타임아웃 설정
            self._start_connection_timeout()
            
            # 호스트 연결 시도
            self.socket.connectToHost(
                self.settings.server.tcp_ip,
                self.settings.server.tcp_port
            )
            
            return True
            
        except Exception as e:
            self.is_connecting = False
            self._handle_connection_error(f"연결 시도 실패: {e}")
            return False

    def disconnect_from_server(self):
        """서버 연결 해제"""
        try:
            # 타이머들 중지
            self.connection_timeout_timer.stop()
            self.reconnect_timer.stop()
            
            # 메시지 큐 정리
            self.message_queue.clear()
            
            # TCP 소켓 연결 해제
            if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
                self.socket.disconnectFromHost()
                if not self.socket.waitForDisconnected(3000):
                    self.socket.abort()
            
            self.is_connecting = False
            
        except Exception as e:
            logger.error(f"연결 해제 실패: {e}")

    def is_connected(self) -> bool:
        """TCP 연결 상태 확인"""
        return (self.socket and 
                self.socket.state() == QTcpSocket.SocketState.ConnectedState)

    # === 요청 메서드 ===
    def request_cctv_a(self) -> bool:
        """CCTV A 영상 요청"""
        self.active_cctv = 'A'
        success = self._send_request(MessageInterface.create_cctv_request, "A", "CCTV A 요청")
        return success

    def request_cctv_b(self) -> bool:
        """CCTV B 영상 요청"""
        self.active_cctv = 'B'
        success = self._send_request(MessageInterface.create_cctv_request, "B", "CCTV B 요청")
        return success

    def request_map(self) -> bool:
        """지도 영상 요청"""
        return self._send_request(
            MessageInterface.create_map_request, 
            None, 
            "지도 요청",
            priority=2
        )

    def request_object_detail(self, object_id: int) -> bool:
        """객체 상세보기 요청"""
        return self._send_request(
            MessageInterface.create_object_detail_request, 
            object_id, 
            f"객체 상세보기 요청 (ID: {object_id})",
            priority=1
        )

    # === 소켓 이벤트 핸들러 ===
    def _on_connected(self):
        """연결 성공 처리"""
        # 상태 초기화
        self.is_connecting = False
        self.connection_timeout_timer.stop()
        self.message_buffer = ""
        self.reconnect_count = 0  # 재연결 카운트 리셋
        
        # 연결 성공 로그 (한번만 출력)
        if not self._connection_successful:
            logger.info(f"TCP 연결 성공 ({self.settings.server.tcp_ip}:{self.settings.server.tcp_port})")
            self._connection_successful = True
        
        # 큐에 있던 메시지들 전송
        self._process_message_queue()
        
        self.connected.emit()

    def _on_disconnected(self):
        """연결 해제 처리"""
        self.is_connecting = False
        self.connection_timeout_timer.stop()
        
        # 연결이 성공했었던 경우에만 해제 로그 출력
        if self._connection_successful:
            logger.info("TCP 연결 해제")
        
        self.disconnected.emit()
        
        # 자동 재연결 시작
        self._start_reconnect()

    def _on_data_ready(self):
        """데이터 수신 처리"""
        try:
            while self.socket.bytesAvailable():
                raw_data = self.socket.readAll().data()
                
                # 통계 업데이트
                self.stats['bytes_received'] += len(raw_data)
                self.stats['last_activity'] = time.time()
                
                # 바이너리 데이터인지 텍스트 데이터인지 확인
                if self._is_binary_data(raw_data):
                    # 바이너리 데이터 처리 (이미지 등)
                    self._handle_binary_data(raw_data)
                else:
                    # 텍스트 데이터 처리
                    try:
                        text_data = raw_data.decode('utf-8')
                        self.message_buffer += text_data
                        # 완전한 메시지들 처리
                        self._process_buffered_messages()
                    except UnicodeDecodeError as e:
                        # 부분적으로 손상된 데이터는 버퍼에서 제거
                        logger.warning(f"부분적으로 손상된 텍스트 데이터 무시: {len(raw_data)} bytes, 오류: {e}")
                        # 디버깅을 위해 처음 몇 바이트 출력
                        if len(raw_data) > 0:
                            hex_data = raw_data[:20].hex()
                            logger.debug(f"손상된 데이터 샘플 (처음 20바이트): {hex_data}")
                        continue
                
        except Exception as e:
            logger.error(f"TCP 데이터 수신 오류: {e}")

    def _is_binary_data(self, data: bytes) -> bool:
        """바이너리 데이터인지 확인"""
        # 첫 몇 바이트가 텍스트 메시지 형식인지 확인
        if len(data) < 10:
            return False
            
        # 메시지 접두사 확인 (예: ME_OD:, MR_CA: 등)
        text_prefixes = [b'ME_OD:', b'ME_FD:', b'ME_BR:', b'ME_RA:', b'ME_RB:', 
                        b'MR_CA:', b'MR_CB:', b'MR_MP:', b'MR_OD:']
        
        for prefix in text_prefixes:
            if data.startswith(prefix):
                if prefix == b'MR_OD:':
                    return self._check_if_contains_image_data(data)
                return False
        
        # 바이너리 데이터로 판단 (이미지 데이터 등)
        return True
    
    def _check_if_contains_image_data(self, data: bytes) -> bool:
        """MR_OD: 응답에 이미지 데이터가 포함되어 있는지 확인"""
        try:
            # MR_OD: 응답에서 콤마를 찾아 필드 분리
            if b',' not in data:
                return False
                
            # 첫 번째 콤마 이후의 데이터 확인
            after_comma = data[data.find(b','):]
            
            # JPEG 시그니처 확인 (0xFF 0xD8 0xFF)
            if b'\xff\xd8\xff' in after_comma:
                logger.debug("MR_OD: 응답에서 JPEG 이미지 데이터 발견")
                return True
                
            # PNG 시그니처 확인 (0x89 0x50 0x4E 0x47)
            if b'\x89PNG' in after_comma:
                logger.debug("MR_OD: 응답에서 PNG 이미지 데이터 발견")
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"이미지 데이터 확인 중 오류: {e}")
            return False

    def _handle_binary_data(self, data: bytes):
        """바이너리 데이터 처리"""
        try:
            # MR_OD: 응답인 경우 특별 처리
            if data.startswith(b'MR_OD:'):
                self._handle_object_detail_binary_response(data)
            # CCTV 프레임 데이터인지 확인
            elif self._is_cctv_frame_data(data):
                self._process_cctv_frame(data)
            else:
                # 기타 바이너리 데이터는 로그만 남김
                logger.debug(f"바이너리 데이터 수신: {len(data)} bytes")
                
        except Exception as e:
            logger.error(f"바이너리 데이터 처리 오류: {e}")
    
    def _handle_object_detail_binary_response(self, data: bytes):
        """MR_OD: 바이너리 응답 처리 (텍스트 + 이미지)"""
        try:
            # MR_OD: 응답에서 텍스트 부분과 이미지 부분 분리
            # 형식: MR_OD:OK,{object_id},{object_type},{area},{timestamp},{image_size},{image_data}
            
            # 텍스트 부분과 이미지 부분을 분리
            # image_size 필드까지 텍스트로 파싱하고, 그 이후는 이미지 데이터
            text_end_pos = -1
            comma_count = 0
            target_commas = 5  # OK,object_id,object_type,area,timestamp,image_size
            
            for i, byte in enumerate(data):
                if byte == ord(b','):
                    comma_count += 1
                    if comma_count == target_commas:
                        text_end_pos = i
                        break
            
            if text_end_pos == -1:
                logger.error("MR_OD: 응답에서 image_size 필드를 찾을 수 없음")
                return
                
            # 텍스트 부분 파싱 (image_size까지)
            text_part = data[:text_end_pos].decode('utf-8')
            logger.debug(f"MR_OD: 텍스트 부분: {text_part}")
            
            # 이미지 데이터 부분
            image_data = data[text_end_pos + 1:]
            
            # 텍스트 부분을 메시지로 처리
            if text_part.startswith("MR_OD:OK"):
                # 성공 응답인 경우 이미지 데이터와 함께 처리
                self._process_object_detail_with_image(text_part, image_data)
            else:
                # 오류 응답인 경우 텍스트만 처리
                self._handle_object_detail_response(text_part)
                
        except Exception as e:
            logger.error(f"MR_OD: 바이너리 응답 처리 오류: {e}")
    
    def _process_object_detail_with_image(self, text_part: str, image_data: bytes):
        """이미지가 포함된 객체 상세보기 응답 처리"""
        try:
            # 텍스트 부분에서 객체 정보 파싱
            # MR_OD:OK,{object_id},{object_type},{area},{timestamp},{image_size}
            parts = text_part.split(',')
            if len(parts) < 6:
                logger.error(f"MR_OD: 응답 필드 수 부족: {len(parts)}")
                return

            # --- 추가: 이미지 데이터 제외한 raw 텍스트 필드 info 로그 ---
            logger.info(f"MR_OD: 이미지 제외 raw 필드: {parts[:6]}")
            # ---
            
            # 객체 정보 생성
            object_id = int(parts[1])
            object_type = MessageParser._parse_object_type(parts[2])
            zone = MessageParser._parse_zone(parts[3])
            timestamp = MessageParser._parse_timestamp(parts[4])
            image_size = int(parts[5])
            
            # 이미지 크기 검증
            if len(image_data) != image_size:
                logger.warning(f"이미지 크기 불일치: {len(image_data)} != {image_size}")
            
            # DetectedObject 생성
            obj = DetectedObject(
                object_id=object_id,
                object_type=object_type,
                zone=zone,
                timestamp=timestamp,
                extra_info=None,
                image_data=image_data
            )
            
            # 시그널 발생
            self.object_detail_response.emit(obj)
            logger.info(f"이미지 포함 객체 상세보기 응답 처리 완료: ID {object_id}")
            
        except Exception as e:
            logger.error(f"이미지 포함 객체 상세보기 처리 오류: {e}")
            self.object_detail_error.emit(str(e))

    def _is_cctv_frame_data(self, data: bytes) -> bool:
        """CCTV 프레임 데이터인지 확인"""
        # 간단한 휴리스틱: JPEG/PNG 시그니처 확인
        jpeg_signatures = [b'\xff\xd8\xff', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1']
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        if data.startswith(png_signature):
            return True
            
        for sig in jpeg_signatures:
            if data.startswith(sig):
                return True
                
        return False

    def _process_cctv_frame(self, data: bytes):
        """CCTV 프레임 데이터 처리"""
        try:
            # OpenCV로 이미지 디코딩
            import cv2
            import numpy as np
            
            frame_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # QImage로 변환
                from PyQt6.QtGui import QImage
                
                # BGR을 RGB로 변환
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                qimage = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # 활성 CCTV에 따라 시그널 발생
                if self.active_cctv:
                    logger.debug(f"CCTV {self.active_cctv} 프레임 수신: {w}x{h}")
                    self.cctv_frame_received.emit(self.active_cctv, qimage, 0)
                else:
                    logger.warning("활성 CCTV가 설정되지 않음")
                
        except Exception as e:
            logger.error(f"CCTV 프레임 처리 오류: {e}")

    def _on_socket_error(self, error):
        """소켓 오류 처리"""
        self.connection_timeout_timer.stop()
        self.is_connecting = False
        
        # 첫 연결 실패만 로그 출력
        if not self._connection_successful and self.reconnect_count == 0:
            error_msg = self.socket.errorString()
            simple_msg = "서버 응답 없음"
            
            if "Connection refused" in error_msg:
                simple_msg = "서버 응답 없음"
            elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                simple_msg = "연결 시간 초과"
            elif "Network" in error_msg:
                simple_msg = "네트워크 오류"
            
            logger.warning(f"TCP 연결 실패 ({self.settings.server.tcp_ip}:{self.settings.server.tcp_port}): {simple_msg}")
        
        self._handle_connection_error("연결 실패")

    def _on_connection_timeout(self):
        """연결 타임아웃 처리"""
        self.is_connecting = False
        
        # 연결 시도 중단
        if self.socket.state() == QTcpSocket.SocketState.ConnectingState:
            self.socket.abort()
        
        self._handle_connection_error("연결 시간 초과")

    def _start_reconnect(self):
        """재연결 시작"""
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start(self.reconnect_interval)

    def _attempt_reconnect(self):
        """재연결 시도"""
        self.reconnect_count += 1
        
        # 재연결 로그는 첫 번째와 이후 5회마다 출력
        if self.reconnect_count == 1 or self.reconnect_count % 5 == 0:
            logger.info(f"TCP 재연결 시도 중... (시도 {self.reconnect_count}회)")
        
        if self.connect_to_server():
            # 연결 성공하면 _on_connected에서 처리
            pass
        else:
            # 실패하면 다시 타이머 시작
            self.reconnect_timer.start(self.reconnect_interval)

    # === 메시지 처리 메서드 ===
    def _process_buffered_messages(self):
        """버퍼된 메시지들을 처리"""
        while '\n' in self.message_buffer:
            line, self.message_buffer = self.message_buffer.split('\n', 1)
            message = line.strip()
            if message:
                self._process_single_message(message)
                self.stats['messages_received'] += 1

    def _process_single_message(self, message: str):
        """단일 메시지 처리"""
        try:
            prefix, data = MessageInterface.parse_message(message)
            
            # 메시지 타입별 처리
            handler_map = {
                MessagePrefix.ME_OD: self._handle_object_detection,
                MessagePrefix.ME_FD: self._handle_first_detection,  # 최초 감지 이벤트
                MessagePrefix.ME_BR: self._handle_bird_risk_change,
                MessagePrefix.ME_RA: self._handle_runway_a_risk_change,
                MessagePrefix.ME_RB: self._handle_runway_b_risk_change,
                MessagePrefix.MR_CA: self._handle_cctv_a_response,
                MessagePrefix.MR_CB: self._handle_cctv_b_response,
                MessagePrefix.MR_MP: self._handle_map_response,
                MessagePrefix.MR_OD: self._handle_object_detail_response
            }
            
            handler = handler_map.get(prefix)
            if handler:
                handler(data)
            else:
                logger.warning(f"알 수 없는 메시지 타입: {prefix}")
                
        except Exception as e:
            logger.error(f"메시지 처리 실패: {e}, 메시지: {message[:100]}")

    def _process_message_queue(self):
        """메시지 큐 처리"""
        processed = 0
        while self.message_queue.size() > 0 and self.is_connected() and processed < 10:
            message = self.message_queue.dequeue()
            if message:
                self._send_message_direct(message)
                processed += 1

    # === 내부 유틸리티 메서드 ===
    def _cleanup_previous_connection(self):
        """이전 연결 정리"""
        if self.socket.state() != QTcpSocket.SocketState.UnconnectedState:
            self.socket.abort()
            self.socket.waitForDisconnected(1000)

    def _setup_socket_signals(self):
        """소켓 시그널 연결"""
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.readyRead.connect(self._on_data_ready)
        self.socket.errorOccurred.connect(self._on_socket_error)

    def _start_connection_timeout(self):
        """연결 타임아웃 타이머 시작"""
        timeout_ms = self.settings.server.connection_timeout * 1000
        self.connection_timeout_timer.start(timeout_ms)

    def _handle_connection_error(self, error_msg: str):
        """연결 오류 처리"""
        self.connection_error.emit(error_msg)
        self._start_reconnect()

    def _send_request(self, create_func: Callable, param: Any, description: str, priority: int = 0) -> bool:
        """요청 메시지 전송"""
        try:
            message = create_func(param) if param is not None else create_func()
            return self._send_command(message, description, priority)
        except Exception:
            return False

    def _send_command(self, command: str, description: str, priority: int = 0) -> bool:
        """명령어 전송"""
        message = command + '\n'
        
        if self.is_connected():
            return self._send_message_direct(message, description)
        else:
            # 연결되지 않은 경우 큐에 저장
            self.message_queue.enqueue(message, priority)
            return False

    def _send_message_direct(self, message: str, description: str = "") -> bool:
        """메시지 직접 전송"""
        try:
            data = message.encode('utf-8')
            bytes_written = self.socket.write(data)
            
            if bytes_written == len(data):
                self.stats['messages_sent'] += 1
                self.stats['bytes_sent'] += len(data)
                self.stats['last_activity'] = time.time()
                return True
            else:
                return False
                
        except Exception:
            return False

    # === 개별 메시지 핸들러 ===
    def _handle_first_detection(self, data: str):
        """최초 객체 감지 이벤트 처리 (ME_FD)"""
        try:
            objects = MessageInterface.parse_object_detection_event(data)
            # 최초 감지 이벤트는 별도 시그널로 전달
            self.first_object_detected.emit(objects)
            logger.info(f"최초 객체 감지 이벤트 처리: {len(objects)}개 객체")
        except Exception as e:
            logger.error(f"최초 객체 감지 이벤트 처리 실패: {e}, 데이터: {data[:100]}")

    def _handle_object_detection(self, data: str):
        """일반 객체 감지 이벤트 처리 (ME_OD)"""
        try:
            objects = MessageInterface.parse_object_detection_event(data)
            self.object_detected.emit(objects)
            logger.debug(f"일반 객체 감지 이벤트 처리: {len(objects)}개 객체")
        except Exception as e:
            logger.error(f"객체 감지 이벤트 처리 실패: {e}, 데이터: {data[:100]}")

    def _handle_bird_risk_change(self, data: str):
        """조류 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_bird_risk_level_event(data)
            self.bird_risk_changed.emit(risk_level)
        except Exception as e:
            logger.error(f"조류 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_runway_a_risk_change(self, data: str):
        """활주로 A 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_runway_risk_level_event(data)
            self.runway_a_risk_changed.emit(risk_level)
        except Exception as e:
            logger.error(f"활주로 A 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_runway_b_risk_change(self, data: str):
        """활주로 B 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_runway_risk_level_event(data)
            self.runway_b_risk_changed.emit(risk_level)
        except Exception as e:
            logger.error(f"활주로 B 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_cctv_a_response(self, data: str):
        """CCTV A 응답 처리"""
        self.cctv_a_response.emit(data)

    def _handle_cctv_b_response(self, data: str):
        """CCTV B 응답 처리"""
        self.cctv_b_response.emit(data)

    def _handle_map_response(self, data: str):
        """지도 응답 처리"""
        self.map_response.emit(data)

    def _handle_object_detail_response(self, data: str):
        """객체 상세보기 응답 처리"""
        try:
            # 응답 성공/실패 여부 확인
            if data.startswith("OK"):
                self._handle_object_detail_success(data)
            elif data.startswith("ERR"):
                self._handle_object_detail_error_response(data)
            else:
                raise Exception("알 수 없는 응답 형식")
        except Exception as e:
            logger.error(f"객체 상세보기 응답 처리 실패: {e}")
            self.object_detail_error.emit(str(e))

    def _handle_object_detail_success(self, data: str):
        """객체 상세보기 성공 응답 처리"""
        try:
            # "OK," 접두사 제거
            payload = data.split(',', 1)[1]
            obj = MessageParser.parse_object_detail_info(payload)
            self.object_detail_response.emit(obj)
        except Exception as e:
            logger.error(f"객체 상세보기 응답 파싱 실패: {e}")
            self.object_detail_error.emit(str(e))

    def _handle_object_detail_error_response(self, data: str):
        """객체 상세보기 오류 응답 처리"""
        try:
            if Constants.Protocol.MESSAGE_SEPARATOR in data:
                _, error_msg = data.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
            else:
                error_msg = "알 수 없는 오류"
                
            self.object_detail_error.emit(error_msg)
            
        except Exception:
            self.object_detail_error.emit("응답 처리 중 오류")