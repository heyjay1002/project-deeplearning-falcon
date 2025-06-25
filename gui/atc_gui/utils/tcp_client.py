from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
from PyQt6.QtGui import QImage
from typing import Optional, Any, Callable
from datetime import datetime
import time
import cv2
import numpy as np
import re

from config import Settings, Constants, MessagePrefix, BirdRiskLevel, RunwayRiskLevel, EventType
from utils.interface import (MessageInterface, MessageParser, 
                           DetectedObject)
from utils.logger import logger


class MessageQueue:
    """메시지 큐 관리 클래스"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = []
        self.max_size = max_size
        
    def enqueue(self, message: str, priority: int = 0):
        """메시지를 우선순위에 따라 큐에 추가"""
        if len(self.queue) >= self.max_size:
            self.queue.pop(0)  # 가장 오래된 메시지 제거
        
        # 우선순위에 따른 삽입 위치 찾기
        insert_pos = len(self.queue)
        for i, (_, msg_priority) in enumerate(self.queue):
            if priority > msg_priority:
                insert_pos = i
                break
        
        self.queue.insert(insert_pos, (message, priority))
    
    def dequeue(self) -> Optional[str]:
        """큐에서 메시지 제거 및 반환"""
        if self.queue:
            message, _ = self.queue.pop(0)
            return message
        return None
    
    def clear(self):
        """큐 초기화"""
        self.queue.clear()
    
    def size(self) -> int:
        """큐 크기 반환"""
        return len(self.queue)


class BinaryDataProcessor:
    """바이너리 데이터 처리 전용 클래스"""
    
    @staticmethod
    def is_binary_data(data: bytes) -> bool:
        """바이너리 데이터인지 확인"""
        if len(data) < 10:
            return False
            
        # 텍스트 메시지 접두사들
        text_prefixes = [b'ME_OD:', b'ME_BR:', b'ME_RA:', b'ME_RB:', 
                        b'MR_CA:', b'MR_CB:', b'MR_MP:']
        
        # 바이너리 데이터를 포함할 수 있는 메시지들
        binary_prefixes = [b'MR_OD:', b'ME_FD:']
        
        for prefix in text_prefixes:
            if data.startswith(prefix):
                return False
        
        for prefix in binary_prefixes:
            if data.startswith(prefix):
                return BinaryDataProcessor._contains_image_data(data)
        
        return True
    
    @staticmethod
    def _contains_image_data(data: bytes) -> bool:
        """이미지 데이터가 포함되어 있는지 확인"""
        try:
            # JPEG/PNG 시그니처 확인
            if b'\xff\xd8\xff' in data or b'\x89PNG' in data:
                return True
            
            # 데이터 크기가 큰 경우 바이너리로 간주
            if len(data) > 1000:
                return True
                
            # UTF-8 디코딩 시도
            try:
                data.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
                
        except Exception:
            return False
    
    @staticmethod
    def is_cctv_frame_data(data: bytes) -> bool:
        """CCTV 프레임 데이터인지 확인"""
        # JPEG/PNG 시그니처 확인
        jpeg_signatures = [b'\xff\xd8\xff', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1']
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        if data.startswith(png_signature):
            return True
            
        for sig in jpeg_signatures:
            if data.startswith(sig):
                return True
                
        return False
    
    @staticmethod
    def extract_text_part_from_binary(data: bytes, message_type: str) -> str:
        """바이너리 메시지에서 텍스트 부분 추출"""
        try:
            if message_type == 'MR_OD':
                # MR_OD:OK,event_type,object_id,object_type,area,timestamp,image_size[,image_data]
                target_commas = 7  # OK,event_type,object_id,object_type,area,timestamp,image_size
            elif message_type == 'ME_FD':
                # ME_FD:event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size,image_data
                target_commas = 8  # event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
            else:
                return ""
            
            comma_count = 0
            text_end_pos = -1
            
            for i, byte in enumerate(data):
                if byte == ord(b','):
                    comma_count += 1
                    if comma_count == target_commas:
                        text_end_pos = i
                        break
            
            if text_end_pos == -1:
                logger.warning(f"{message_type}: 텍스트 부분을 찾을 수 없음")
                return ""
                
            return data[:text_end_pos].decode('utf-8')
            
        except Exception as e:
            logger.error(f"{message_type} 텍스트 부분 추출 오류: {e}")
            return ""
    
    @staticmethod
    def calculate_expected_size(data: bytes, message_type: str) -> int:
        """예상 바이너리 데이터 크기 계산"""
        try:
            text_part = BinaryDataProcessor.extract_text_part_from_binary(data, message_type)
            if not text_part:
                return 0
            
            parts = text_part.split(',')
            
            if message_type == 'MR_OD' and len(parts) >= 7:
                # MR_OD:OK,event_type,object_id,object_type,area,timestamp,image_size[,image_data]
                # parts[0] = "MR_OD:OK"
                # parts[1] = event_type
                # parts[2] = object_id
                # parts[3] = object_type
                # parts[4] = area
                # parts[5] = timestamp
                # parts[6] = image_size
                image_size = int(parts[6])  # parts[6]이 image_size
                text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
                return text_size + image_size
            elif message_type == 'ME_FD' and len(parts) >= 8:
                # ME_FD:event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
                image_size = int(parts[7])
                text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
                return text_size + image_size
            
            return 0
            
        except Exception as e:
            logger.error(f"{message_type} 크기 계산 오류: {e}")
            return 0


class TcpClient(QObject):
    """TCP 클라이언트 - 서버와의 통신 관리"""
    
    # === 시그널 정의 ===
    # 연결 상태 시그널
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    
    # 이벤트 시그널
    object_detected = pyqtSignal(list)
    first_object_detected = pyqtSignal(list)  # 최초 감지 이벤트용
    bird_risk_changed = pyqtSignal(BirdRiskLevel)
    runway_a_risk_changed = pyqtSignal(RunwayRiskLevel)
    runway_b_risk_changed = pyqtSignal(RunwayRiskLevel)
    
    # 응답 시그널
    cctv_a_response = pyqtSignal(str)
    cctv_b_response = pyqtSignal(str)
    map_response = pyqtSignal(str)
    object_detail_response = pyqtSignal(DetectedObject)
    object_detail_error = pyqtSignal(str)
    
    # CCTV 프레임 시그널
    cctv_frame_received = pyqtSignal(str, QImage, int)  # (카메라 ID, QImage, 이미지ID)

    def __init__(self):
        super().__init__()
        
        # 설정 및 인터페이스
        self.settings = Settings.get_instance()
        self.message_interface = MessageInterface()
        self.message_queue = MessageQueue()
        self.binary_processor = BinaryDataProcessor()
        
        # TCP 소켓 및 연결 관리
        self.socket = QTcpSocket(self)
        self._setup_socket_signals()
        
        # 타이머 설정
        self._setup_timers()
        
        # 상태 관리
        self.message_buffer = ""
        self.is_connecting = False
        self.connection_start_time = None
        
        # 바이너리 데이터 처리 변수들
        self.binary_buffer = b''
        self.expected_binary_size = 0
        self.is_receiving_binary = False
        self.binary_start_time = None
        self.current_binary_type = None  # 현재 처리 중인 바이너리 메시지 타입
        
        # 재연결 관리
        self.reconnect_count = 0
        self.max_reconnect_attempts = None  # 무한 재시도
        self.reconnect_interval = 5000  # 5초
        
        # 로그 상태 추적
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

    # === 초기화 메서드 ===
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

    def _setup_socket_signals(self):
        """소켓 시그널 연결"""
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.readyRead.connect(self._on_data_ready)
        self.socket.errorOccurred.connect(self._on_socket_error)

    # === 공개 인터페이스 메서드 ===
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
            
            # 바이너리 버퍼 정리
            self._reset_binary_buffer()
            
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
        return self._send_request(MessageInterface.create_cctv_request, "A", "CCTV A 요청")

    def request_cctv_b(self) -> bool:
        """CCTV B 영상 요청"""
        self.active_cctv = 'B'
        return self._send_request(MessageInterface.create_cctv_request, "B", "CCTV B 요청")

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
        self.is_connecting = False
        self.connection_timeout_timer.stop()
        self.message_buffer = ""
        self.reconnect_count = 0
        
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
                
                # 바이너리 데이터 수신 중인 경우
                if self.is_receiving_binary:
                    self._handle_binary_buffer(raw_data)
                    continue
                
                # 바이너리 데이터인지 텍스트 데이터인지 확인
                if self.binary_processor.is_binary_data(raw_data):
                    self._handle_binary_data(raw_data)
                else:
                    # 텍스트 데이터 처리
                    try:
                        text_data = raw_data.decode('utf-8')
                        self.message_buffer += text_data
                        self._process_buffered_messages()
                    except UnicodeDecodeError:
                        # UTF-8 디코딩 실패 시 바이너리 데이터로 재처리
                        logger.debug("UTF-8 디코딩 실패, 바이너리 데이터로 재처리")
                        self._handle_binary_data(raw_data)
                        
        except Exception as e:
            logger.error(f"TCP 데이터 수신 오류: {e}")

    def _handle_binary_buffer(self, data: bytes):
        """바이너리 데이터 버퍼링 처리"""
        try:
            self.binary_buffer += data
            
            # 타임아웃 체크 (30초)
            if self.binary_start_time and (time.time() - self.binary_start_time) > 30:
                logger.error("바이너리 데이터 수신 타임아웃")
                self._reset_binary_buffer()
                return
            
            # 메시지 타입별 처리
            if self.current_binary_type in ['MR_OD', 'ME_FD']:
                expected_size = self.binary_processor.calculate_expected_size(
                    self.binary_buffer, self.current_binary_type
                )
                
                if expected_size > 0 and len(self.binary_buffer) >= expected_size:
                    logger.info(f"{self.current_binary_type} 완전한 데이터 수신: {len(self.binary_buffer)} bytes")
                    self._process_binary_message(self.current_binary_type, self.binary_buffer)
                    self._reset_binary_buffer()
                elif len(self.binary_buffer) > 50000:  # 50KB 제한
                    logger.warning(f"{self.current_binary_type} 크기 제한 초과, 강제 처리")
                    self._process_binary_message(self.current_binary_type, self.binary_buffer)
                    self._reset_binary_buffer()
            
            # CCTV 프레임 처리
            elif self.binary_processor.is_cctv_frame_data(self.binary_buffer):
                if len(self.binary_buffer) > 1000:  # 1KB 이상
                    logger.info(f"CCTV 프레임 처리: {len(self.binary_buffer)} bytes")
                    self._process_cctv_frame(self.binary_buffer)
                    self._reset_binary_buffer()
                        
        except Exception as e:
            logger.error(f"바이너리 버퍼 처리 오류: {e}")
            self._reset_binary_buffer()

    def _handle_binary_data(self, data: bytes):
        """바이너리 데이터 초기 처리"""
        try:
            # 메시지 타입 확인
            if data.startswith(b'MR_OD:'):
                self.current_binary_type = 'MR_OD'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"MR_OD 바이너리 수신 시작: {len(data)} bytes")
                
            elif data.startswith(b'ME_FD:'):
                self.current_binary_type = 'ME_FD'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"ME_FD 바이너리 수신 시작: {len(data)} bytes")
                logger.info(f"ME_FD raw 데이터 (처음 200바이트): {data[:200]}")
                
                # ME_FD 텍스트 부분 미리 추출해서 출력
                try:
                    text_part = self.binary_processor.extract_text_part_from_binary(data, 'ME_FD')
                    if text_part:
                        logger.info(f"ME_FD 초기 텍스트 부분: {text_part}")
                except Exception as e:
                    logger.debug(f"ME_FD 초기 텍스트 추출 실패: {e}")
                
            elif self.binary_processor.is_cctv_frame_data(data):
                self.current_binary_type = 'CCTV_FRAME'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"CCTV 프레임 수신 시작: {len(data)} bytes")
                
            else:
                logger.debug(f"기타 바이너리 데이터: {len(data)} bytes")
                
            # 즉시 처리 가능한지 확인
            self._handle_binary_buffer(b'')  # 빈 데이터로 호출하여 기존 버퍼 확인
                
        except Exception as e:
            logger.error(f"바이너리 데이터 처리 오류: {e}")
            self._reset_binary_buffer()

    def _process_binary_message(self, message_type: str, data: bytes):
        """바이너리 메시지 처리"""
        try:
            if message_type == 'MR_OD':
                self._handle_object_detail_binary_response(data)
            elif message_type == 'ME_FD':
                self._handle_first_detection_binary_response(data)
            elif message_type == 'CCTV_FRAME':
                self._process_cctv_frame(data)
            else:
                logger.warning(f"알 수 없는 바이너리 메시지 타입: {message_type}")
                
        except Exception as e:
            logger.error(f"바이너리 메시지 처리 오류: {e}")

    def _handle_object_detail_binary_response(self, data: bytes):
        """MR_OD 바이너리 응답 처리"""
        try:
            # 텍스트 부분과 이미지 부분 분리
            text_part = self.binary_processor.extract_text_part_from_binary(data, 'MR_OD')
            if not text_part:
                logger.error("MR_OD: 텍스트 부분 추출 실패")
                return
            
            # 이미지 데이터 추출
            text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
            image_data = data[text_size:]
            
            # 텍스트 부분 처리
            self._process_object_detail_with_image(text_part, image_data)
                
        except Exception as e:
            logger.error(f"MR_OD 바이너리 응답 처리 오류: {e}")
    
    def _handle_first_detection_binary_response(self, data: bytes):
        """ME_FD 바이너리 응답 처리"""
        try:
            # 텍스트 부분과 이미지 부분 분리  
            text_part = self.binary_processor.extract_text_part_from_binary(data, 'ME_FD')
            if not text_part:
                logger.error("ME_FD: 텍스트 부분 추출 실패")
                return
            
            # 이미지 데이터 추출
            text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
            image_data = data[text_size:]
            
            # ME_FD: 프리픽스 제거
            if text_part.startswith('ME_FD:'):
                text_part = text_part[6:]  # 'ME_FD:' 제거
            
            # 터미널에 텍스트 부분 출력 (이미지 제외)
            logger.info(f"ME_FD 텍스트 데이터: {text_part}")
            logger.info(f"ME_FD 이미지 크기: {len(image_data)} bytes")
            
            # 텍스트 부분 처리
            self._process_first_detection_with_image(text_part, image_data)

        except Exception as e:
            logger.error(f"ME_FD 바이너리 응답 처리 오류: {e}")

    def _process_first_detection_with_image(self, text_part: str, image_data: bytes):
        """이미지가 포함된 최초 감지 이벤트 처리"""
        try:
            # 텍스트 부분에서 객체 정보 파싱
            # 형식: event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
            parts = text_part.split(',')
            
            if len(parts) < 8:
                logger.error(f"ME_FD: 필드 수 부족: {len(parts)}")
                return

            # 객체 정보 생성
            event_type = MessageParser._parse_event_type(parts[0])
            object_id = int(parts[1])
            object_type = MessageParser._parse_object_type(parts[2])
            x_coord = float(parts[3])
            y_coord = float(parts[4])
            area = MessageParser._parse_area(parts[5])
            timestamp = MessageParser._parse_timestamp(parts[6])
            image_size = int(parts[7])

            logger.debug(f"ME_FD 바이너리 파싱 결과: ID={object_id}, Type={object_type.value}, Pos=({x_coord}, {y_coord}), Area={area.value}, EventType={event_type.value if event_type else 'None'}, ImageSize={image_size}")

            # 이미지 크기 검증
            if len(image_data) != image_size:
                logger.warning(f"ME_FD 이미지 크기 불일치: {len(image_data)} != {image_size}")

            # DetectedObject 생성
            obj = DetectedObject(
                object_id=object_id,
                object_type=object_type,
                x_coord=x_coord,
                y_coord=y_coord,
                area=area,
                event_type=event_type,
                timestamp=timestamp,
                state_info=None,
                image_data=image_data
            )

            # 최초 감지 이벤트 시그널 발생
            self.first_object_detected.emit([obj])
            logger.info(f"이미지 포함 최초 감지 이벤트 처리 완료: ID {object_id}")

        except Exception as e:
            logger.error(f"이미지 포함 최초 감지 이벤트 처리 오류: {e}")

    def _process_object_detail_with_image(self, text_part: str, image_data: bytes):
        """이미지가 포함된 객체 상세보기 응답 처리"""
        try:
            # MR_OD:OK,event_type,object_id,object_type,area,timestamp,image_size[,image_data]
            prefix = "MR_OD:OK,"
            if text_part.startswith(prefix):
                data_body = text_part[len(prefix):]
            else:
                logger.error(f"MR_OD: prefix 누락: {text_part}")
                return
                
            parts = data_body.split(',')
            
            if len(parts) < 6:
                logger.error(f"MR_OD: 필드 수 부족: {len(parts)}")
                return

            # 객체 정보 생성
            # parts[0] = event_type
            # parts[1] = object_id
            # parts[2] = object_type
            # parts[3] = area
            # parts[4] = timestamp
            # parts[5] = image_size
            event_type = MessageParser._parse_event_type(parts[0])
            object_id = int(parts[1])
            object_type = MessageParser._parse_object_type(parts[2])
            area = MessageParser._parse_area(parts[3])
            timestamp = MessageParser._parse_timestamp(parts[4])
            image_size = int(parts[5])

            # 이미지 크기 검증
            if len(image_data) != image_size:
                logger.warning(f"이미지 크기 불일치: {len(image_data)} != {image_size}")

            # DetectedObject 생성
            obj = DetectedObject(
                event_type=event_type,
                object_id=object_id,
                object_type=object_type,
                x_coord=0.0,
                y_coord=0.0,
                area=area,
                timestamp=timestamp,
                state_info=None,
                image_data=image_data
            )

            # 시그널 발생
            self.object_detail_response.emit(obj)
            logger.info(f"이미지 포함 객체 상세보기 응답 처리 완료: ID {object_id}")

        except Exception as e:
            logger.error(f"이미지 포함 객체 상세보기 응답 처리 오류: {e}")
            self.object_detail_error.emit(str(e))

    def _process_cctv_frame(self, data: bytes):
        """CCTV 프레임 데이터 처리"""
        try:
            # OpenCV로 이미지 디코딩
            frame_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # BGR을 RGB로 변환
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # QImage 생성 및 복사본 반환
                qimage = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                qimage_copy = qimage.copy()
                
                # 활성 CCTV에 따라 시그널 발생
                if self.active_cctv:
                    logger.debug(f"CCTV {self.active_cctv} 프레임 수신: {w}x{h}")
                    self.cctv_frame_received.emit(self.active_cctv, qimage_copy, 0)
                else:
                    logger.warning("활성 CCTV가 설정되지 않음")
                
        except Exception as e:
            logger.error(f"CCTV 프레임 처리 오류: {e}")

    def _reset_binary_buffer(self):
        """바이너리 버퍼 초기화"""
        self.binary_buffer = b''
        self.expected_binary_size = 0
        self.is_receiving_binary = False
        self.binary_start_time = None
        self.current_binary_type = None

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
        
        if self.socket.state() == QTcpSocket.SocketState.ConnectingState:
            self.socket.abort()
        
        self._handle_connection_error("연결 시간 초과")

    # === 재연결 관리 ===
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
            pass  # 성공하면 _on_connected에서 처리
        else:
            self.reconnect_timer.start(self.reconnect_interval)

    # === 메시지 처리 메서드 ===
    def _process_buffered_messages(self):
        """버퍼된 메시지들을 처리"""
        try:
            # 줄바꿈으로 분리
            while '\n' in self.message_buffer:
                line, self.message_buffer = self.message_buffer.split('\n', 1)
                message = line.strip()
                if message:
                    self._process_single_message(message)
                    self.stats['messages_received'] += 1
            
            # 줄바꿈이 없는 경우에도 메시지 프리픽스로 분리 시도
            if self.message_buffer and not '\n' in self.message_buffer:
                # 메시지 프리픽스들 확인
                prefixes = ['ME_OD:', 'ME_FD:', 'ME_BR:', 'ME_RA:', 'ME_RB:', 
                           'MR_CA:', 'MR_CB:', 'MR_MP:', 'MR_OD:']
                
                for prefix in prefixes:
                    if prefix in self.message_buffer:
                        # 프리픽스 이전의 잘못된 데이터 제거
                        prefix_pos = self.message_buffer.find(prefix)
                        if prefix_pos > 0:
                            invalid_part = self.message_buffer[:prefix_pos]
                            logger.warning(f"잘못된 메시지 데이터 제거: '{invalid_part}'")
                            self.message_buffer = self.message_buffer[prefix_pos:]
                        
                        # 완전한 메시지인지 확인 (세미콜론이나 다른 구분자로 끝나는지)
                        if ';' in self.message_buffer:
                            # 세미콜론으로 구분된 메시지들 처리
                            parts = self.message_buffer.split(';')
                            for i, part in enumerate(parts[:-1]):  # 마지막 부분은 버퍼에 남김
                                if part.strip():
                                    self._process_single_message(part.strip())
                                    self.stats['messages_received'] += 1
                            
                            # 마지막 부분을 버퍼에 남김
                            self.message_buffer = parts[-1]
                            break
                        else:
                            # 단일 메시지인 경우 처리
                            message = self.message_buffer.strip()
                            if message:
                                self._process_single_message(message)
                                self.stats['messages_received'] += 1
                                self.message_buffer = ""
                            break
                
                # 프리픽스가 없는 경우, 숫자로 시작하는 잘못된 데이터 제거
                if self.message_buffer and not any(prefix in self.message_buffer for prefix in prefixes):
                    # 숫자로 시작하는 데이터 제거
                    if re.match(r'^\d+', self.message_buffer):
                        logger.warning(f"숫자로 시작하는 잘못된 데이터 제거: '{self.message_buffer}'")
                        self.message_buffer = ""
                            
        except Exception as e:
            logger.error(f"버퍼된 메시지 처리 오류: {e}")
            # 오류 발생 시 버퍼 초기화
            self.message_buffer = ""

    def _process_single_message(self, message: str):
        """단일 메시지 처리"""
        try:
            # 메시지가 너무 짧거나 잘못된 형식인지 확인
            if len(message) < 3 or ':' not in message:
                return
            
            # 메시지 파싱
            prefix, data = MessageInterface.parse_message(message)
            
            # 메시지 타입별 처리 - 통합된 핸들러 맵
            handler_map = {
                MessagePrefix.ME_OD: self._handle_object_detection,
                MessagePrefix.ME_FD: self._handle_first_detection,
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
                
        except ValueError as e:
            # 메시지 파싱 오류 (잘못된 형식) - 무시
            pass
        except Exception as e:
            # 기타 오류
            logger.error(f"메시지 처리 실패: {e}, 메시지: '{message[:100]}'")

    def _process_message_queue(self):
        """메시지 큐 처리"""
        processed = 0
        while self.message_queue.size() > 0 and self.is_connected() and processed < 10:
            message = self.message_queue.dequeue()
            if message:
                self._send_message_direct(message)
                processed += 1

    # === 메시지 전송 메서드 ===
    def _send_request(self, create_func: Callable, param: Any, description: str, priority: int = 0) -> bool:
        """요청 메시지 전송"""
        try:
            message = create_func(param) if param is not None else create_func()
            return self._send_command(message, description, priority)
        except Exception as e:
            logger.error(f"요청 메시지 생성 실패: {e}")
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
                logger.warning(f"메시지 전송 불완전: {bytes_written}/{len(data)} bytes")
                return False
                
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            return False

    # === 개별 메시지 핸들러 ===
    def _handle_first_detection(self, data: str):
        """최초 객체 감지 이벤트 처리 (ME_FD) - 수정된 인터페이스 사용"""
        try:
            logger.debug(f"ME_FD 이벤트 수신: {data[:200]}...")
            objects = MessageInterface.parse_first_detection_event(data)
            logger.debug(f"ME_FD 파싱 결과: {len(objects)}개 객체")
            for i, obj in enumerate(objects):
                logger.debug(f"ME_FD 객체 {i+1}: ID={obj.object_id}, Type={obj.object_type.value}, Pos=({obj.x_coord}, {obj.y_coord}), Area={obj.area.value}")
            self.first_object_detected.emit(objects)
            logger.info(f"최초 객체 감지 이벤트 처리: {len(objects)}개 객체")
        except Exception as e:
            logger.error(f"최초 객체 감지 이벤트 처리 실패: {e}, 데이터: {data[:100]}")

    def _handle_object_detection(self, data: str):
        """일반 객체 감지 이벤트 처리 (ME_OD)"""
        try:
            logger.debug(f"ME_OD 이벤트 수신: {data[:200]}...")
            objects = MessageInterface.parse_object_detection_event(data)
            logger.debug(f"ME_OD 파싱 결과: {len(objects)}개 객체")
            for i, obj in enumerate(objects):
                logger.debug(f"ME_OD 객체 {i+1}: ID={obj.object_id}, Type={obj.object_type.value}, Pos=({obj.x_coord}, {obj.y_coord}), Area={obj.area.value}")
            self.object_detected.emit(objects)
            logger.debug(f"일반 객체 감지 이벤트 처리: {len(objects)}개 객체")
        except Exception as e:
            logger.error(f"객체 감지 이벤트 처리 실패: {e}, 데이터: {data[:100]}")

    def _handle_bird_risk_change(self, data: str):
        """조류 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_bird_risk_level_event(data)
            self.bird_risk_changed.emit(risk_level)
            logger.info(f"조류 위험도 변경: {risk_level.value}")
        except Exception as e:
            logger.error(f"조류 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_runway_a_risk_change(self, data: str):
        """활주로 A 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_runway_risk_level_event(data)
            self.runway_a_risk_changed.emit(risk_level)
            logger.info(f"활주로 A 위험도 변경: {risk_level.value}")
        except Exception as e:
            logger.error(f"활주로 A 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_runway_b_risk_change(self, data: str):
        """활주로 B 위험도 변경 이벤트 처리"""
        try:
            risk_level = MessageInterface.parse_runway_risk_level_event(data)
            self.runway_b_risk_changed.emit(risk_level)
            logger.info(f"활주로 B 위험도 변경: {risk_level.value}")
        except Exception as e:
            logger.error(f"활주로 B 위험도 변경 이벤트 처리 실패: {e}, 데이터: {data}")

    def _handle_cctv_a_response(self, data: str):
        """CCTV A 응답 처리"""
        logger.debug(f"CCTV A 응답: {data}")
        self.cctv_a_response.emit(data)

    def _handle_cctv_b_response(self, data: str):
        """CCTV B 응답 처리"""
        logger.debug(f"CCTV B 응답: {data}")
        self.cctv_b_response.emit(data)

    def _handle_map_response(self, data: str):
        """지도 응답 처리"""
        logger.debug(f"지도 응답: {data}")
        self.map_response.emit(data)

    def _handle_object_detail_response(self, data: str):
        """객체 상세보기 응답 처리"""
        try:
            logger.debug(f"MR_OD 응답 수신: {data[:200]}...")
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
            logger.debug(f"MR_OD 성공 응답 처리: {data[:200]}...")
            # "OK," 접두사 제거
            payload = data.split(',', 1)[1]
            obj = MessageParser.parse_object_detail_info(payload, b'')  # 텍스트만 있는 경우
            logger.debug(f"MR_OD 파싱 결과: ID={obj.object_id}, Type={obj.object_type.value}, Area={obj.area.value}, EventType={obj.event_type.value if obj.event_type else 'None'}")
            self.object_detail_response.emit(obj)
            logger.info(f"객체 상세보기 응답 처리 완료: ID {obj.object_id}")
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
                
            logger.warning(f"객체 상세보기 오류: {error_msg}")
            self.object_detail_error.emit(error_msg)
            
        except Exception:
            self.object_detail_error.emit("응답 처리 중 오류")

    # === 내부 유틸리티 메서드 ===
    def _cleanup_previous_connection(self):
        """이전 연결 정리"""
        if self.socket.state() != QTcpSocket.SocketState.UnconnectedState:
            self.socket.abort()
            self.socket.waitForDisconnected(1000)

    def _start_connection_timeout(self):
        """연결 타임아웃 타이머 시작"""
        timeout_ms = self.settings.server.connection_timeout * 1000
        self.connection_timeout_timer.start(timeout_ms)

    def _handle_connection_error(self, error_msg: str):
        """연결 오류 처리"""
        self.connection_error.emit(error_msg)
        self._start_reconnect()

    # === 상태 조회 메서드 ===
    def get_connection_stats(self) -> dict:
        """연결 통계 반환"""
        return {
            'connected': self.is_connected(),
            'messages_sent': self.stats['messages_sent'],
            'messages_received': self.stats['messages_received'],
            'bytes_sent': self.stats['bytes_sent'],
            'bytes_received': self.stats['bytes_received'],
            'connection_attempts': self.stats['connection_attempts'],
            'reconnect_count': self.reconnect_count,
            'queue_size': self.message_queue.size(),
            'active_cctv': self.active_cctv,
            'last_activity': self.stats['last_activity']
        }

    def get_binary_buffer_status(self) -> dict:
        """바이너리 버퍼 상태 반환"""
        return {
            'is_receiving': self.is_receiving_binary,
            'buffer_size': len(self.binary_buffer),
            'expected_size': self.expected_binary_size,
            'message_type': self.current_binary_type,
            'start_time': self.binary_start_time
        }