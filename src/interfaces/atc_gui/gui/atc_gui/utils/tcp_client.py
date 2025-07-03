from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
from PyQt6.QtGui import QImage
from typing import Optional, Any, Callable
from datetime import datetime
import time
import cv2
import numpy as np
import re

from config import Settings, Constants, MessagePrefix, BirdRiskLevel, RunwayRiskLevel, EventType, ObjectType, AirportArea
from utils.interface import (MessageInterface, MessageParser, 
                           DetectedObject, AccessControlSettings, PilotLog, ObjectDetectionLog, BirdRiskLog)
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
            
        # 텍스트 메시지 접두사들 (로그 응답 추가)
        text_prefixes = [b'ME_OD:', b'ME_BR:', b'ME_RA:', b'ME_RB:', 
                        b'MR_CA:', b'MR_CB:', b'MR_MP:',
                        b'AR_AC:', b'AR_UA:',  # 출입 제어 응답
                        b'LR_BL:', b'LR_OL:', b'LR_RL:']  # 로그 응답들
        
        # 바이너리 데이터를 포함할 수 있는 메시지들
        binary_prefixes = [b'MR_OD:', b'ME_FD:', b'LR_OI:']  # LR_OI 추가
        
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
                # ME_FD:event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
                target_commas = 8  # event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
            elif message_type == 'LR_OI':
                # LR_OI:response,image_size,image_data
                target_commas = 2  # response,image_size
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
                logger.warning(f"{message_type}: 텍스트 부분 추출 실패")
                return 0
            
            parts = text_part.split(',')
            logger.debug(f"{message_type} 텍스트 분석: '{text_part}', parts: {parts}")
            
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
                expected_size = text_size + image_size
                logger.debug(f"MR_OD 크기 계산: 텍스트={text_size}, 이미지={image_size}, 총={expected_size}")
                return expected_size
            elif message_type == 'ME_FD' and len(parts) >= 8:
                # ME_FD 메시지 구조 분석
                # 8개 필드: ME_FD:event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
                # 9개 필드: ME_FD:event_type,object_id,object_type,x_coord,y_coord,area,timestamp,state_info,image_size
                
                if len(parts) == 8:
                    # 8개 필드: 마지막이 image_size
                    image_size = int(parts[7])
                    logger.debug(f"ME_FD (8개 필드): image_size={image_size}")
                elif len(parts) >= 9:
                    # 9개 필드: 8번째=state_info, 9번째=image_size
                    state_info = parts[7]
                    image_size = int(parts[8])
                    logger.debug(f"ME_FD (9개 필드): state_info={state_info}, image_size={image_size}")
                else:
                    logger.warning(f"ME_FD: 예상치 못한 필드 수 {len(parts)}")
                    return 0
                
                text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
                expected_size = text_size + image_size
                logger.debug(f"ME_FD 크기 계산: 텍스트={text_size}, 이미지={image_size}, 총={expected_size}")
                return expected_size
            elif message_type == 'LR_OI' and len(parts) >= 2:
                # LR_OI:response,image_size,image_data
                # parts[0] = "LR_OI:response"  
                # parts[1] = image_size
                image_size = int(parts[1])  # parts[1]이 image_size
                text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
                expected_size = text_size + image_size
                logger.debug(f"LR_OI 크기 계산: 텍스트='{text_part}'({text_size}), 이미지={image_size}, 총={expected_size}")
                return expected_size
            else:
                logger.warning(f"{message_type}: 부족한 파트 수 (필요: {2 if message_type == 'LR_OI' else 7}, 실제: {len(parts)})")
            
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
    
    # 출입 제어 시그널
    access_control_response = pyqtSignal(AccessControlSettings)  # 출입 제어 설정 응답
    access_control_update_response = pyqtSignal(bool, str)  # 업데이트 응답 (성공여부, 메시지)
    access_control_error = pyqtSignal(str)  # 출입 제어 오류
    
    # 로그 시그널
    pilot_log_response = pyqtSignal(list)  # 파일럿 로그 응답
    pilot_log_error = pyqtSignal(str)  # 파일럿 로그 오류
    object_detection_log_response = pyqtSignal(list)  # 객체 감지 로그 응답
    object_detection_log_error = pyqtSignal(str)  # 객체 감지 로그 오류
    bird_risk_log_response = pyqtSignal(list)  # 조류 위험도 로그 응답
    bird_risk_log_error = pyqtSignal(str)  # 조류 위험도 로그 오류
    # 로그 페이지 전용 객체 이미지 시그널
    log_object_image_response = pyqtSignal(object)  # 로그 페이지 전용 객체 이미지 응답
    log_object_image_error = pyqtSignal(str)  # 로그 페이지 전용 객체 이미지 오류

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
        
        # 객체 이미지 조회 상태 추적
        self.requested_object_id = None  # LC_OI 요청 시 객체 ID 저장
        self.is_log_page_request = False  # 로그 페이지에서 요청한 건지 구분

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
        logger.info(f"객체 상세보기 요청 시작: ID={object_id}")
        # 객체 ID 저장 (LR_OI 응답에서 사용)
        self.requested_object_id = object_id
        self.is_log_page_request = False  # 메인 페이지 요청 표시
        result = self._send_request(
            MessageInterface.create_object_detail_request, 
            object_id, 
            f"객체 상세보기 요청 (ID: {object_id})",
            priority=1
        )
        logger.info(f"객체 상세보기 요청 결과: {result}, ID={object_id}")
        return result

    def request_log_object_image(self, object_id: int) -> bool:
        """로그 페이지 전용 객체 이미지 요청"""
        logger.info(f"로그 페이지 객체 이미지 요청 시작: ID={object_id}")
        # 객체 ID 저장 (LR_OI 응답에서 사용)
        self.requested_object_id = object_id
        self.is_log_page_request = True  # 로그 페이지 요청 표시
        result = self._send_request(
            MessageInterface.create_object_detail_request, 
            object_id, 
            f"로그 페이지 객체 이미지 요청 (ID: {object_id})",
            priority=1
        )
        logger.info(f"로그 페이지 객체 이미지 요청 결과: {result}, ID={object_id}")
        return result

    def request_access_control_settings(self) -> bool:
        """출입 제어 설정 요청"""
        return self._send_request(
            MessageInterface.create_access_control_request,
            None,
            "출입 제어 설정 요청",
            priority=1
        )

    def update_access_control_settings(self, settings: AccessControlSettings) -> bool:
        """출입 제어 설정 업데이트"""
        logger.info(f"출입 제어 설정 업데이트 요청: {settings.to_dict()}")
        return self._send_request(
            MessageInterface.create_access_control_update,
            settings,
            "출입 제어 설정 업데이트",
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
                logger.debug(f"raw_data: {raw_data}")
                
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
            if self.current_binary_type in ['MR_OD', 'ME_FD', 'LR_OI']:
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
            logger.debug(f"바이너리 데이터 처리 시작: {len(data)} bytes, 시작: {data[:20]}")
            
            # 메시지 타입 확인
            if data.startswith(b'MR_OD:'):
                self.current_binary_type = 'MR_OD'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"MR_OD 바이너리 수신 시작: {len(data)} bytes")
                
            elif data.startswith(b'ME_FD:'):
                # ME_FD 데이터에 여러 ME_FD가 포함되어 있는지 확인
                data_str = data.decode('utf-8', errors='ignore')
                me_fd_count = data_str.count('ME_FD:')
                
                if me_fd_count > 1:
                    logger.info(f"🔍 여러 ME_FD 감지: {me_fd_count}개")
                    self._process_multiple_me_fd_binary(data_str)
                else:
                    # 단일 ME_FD 처리
                    self.current_binary_type = 'ME_FD'
                    self.is_receiving_binary = True
                    self.binary_start_time = time.time()
                    self.binary_buffer = data
                    logger.info(f"ME_FD 바이너리 수신 시작: {len(data)} bytes")
                    
                    # ME_FD 텍스트 부분 미리 추출해서 출력
                    try:
                        text_part = self.binary_processor.extract_text_part_from_binary(data, 'ME_FD')
                        if text_part:
                            logger.debug(f"ME_FD 초기 텍스트 부분: {text_part}")
                    except Exception as e:
                        logger.debug(f"ME_FD 초기 텍스트 추출 실패: {e}")
                    
            elif data.startswith(b'LR_OI:'):
                self.current_binary_type = 'LR_OI'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"LR_OI 바이너리 수신 시작: {len(data)} bytes")
                
                # LR_OI 텍스트 부분 미리 추출해서 출력
                try:
                    text_part = self.binary_processor.extract_text_part_from_binary(data, 'LR_OI')
                    if text_part:
                        logger.debug(f"LR_OI 초기 텍스트 부분: {text_part}")
                except Exception as e:
                    logger.debug(f"LR_OI 초기 텍스트 추출 실패: {e}")
                
            elif self.binary_processor.is_cctv_frame_data(data):
                self.current_binary_type = 'CCTV_FRAME'
                self.is_receiving_binary = True
                self.binary_start_time = time.time()
                self.binary_buffer = data
                logger.info(f"CCTV 프레임 수신 시작: {len(data)} bytes")
                
            else:
                # 텍스트로 변환 시도해서 텍스트 응답인지 확인
                try:
                    text_data = data.decode('utf-8', errors='ignore')
                    
                    # ME_OD와 ME_FD가 혼재된 패킷인지 확인
                    if 'ME_OD:' in text_data and 'ME_FD:' in text_data:
                        logger.info(f"🔍 ME_OD와 ME_FD 혼재 패킷 감지!")
                        self._process_mixed_me_od_me_fd_packet(text_data)
                        return
                    
                    # 출입제어 응답 또는 로그 응답인지 확인
                    if ('AR_AC' in text_data or 'AR_UA' in text_data or 
                        'LR_BL' in text_data or 'LR_OL' in text_data or 'LR_RL' in text_data):
                        logger.info(f"텍스트 응답이 바이너리로 분류됨, 재처리: {text_data[:100]}...")
                        # 텍스트 메시지로 재처리
                        self._process_single_message(text_data)
                        return
                    else:
                        logger.debug(f"기타 바이너리 데이터: {len(data)} bytes, 내용: {text_data[:50]}...")
                except:
                    logger.debug(f"알 수 없는 바이너리 데이터: {len(data)} bytes")
                
            # 즉시 처리 가능한지 확인
            self._handle_binary_buffer(b'')  # 빈 데이터로 호출하여 기존 버퍼 확인
                
        except Exception as e:
            logger.error(f"바이너리 데이터 처리 오류: {e}")
            self._reset_binary_buffer()

    def _process_mixed_me_od_me_fd_packet(self, data_str: str):
        """ME_OD와 ME_FD가 혼재된 패킷 처리"""
        try:
            logger.info(f"=== ME_OD와 ME_FD 혼재 패킷 처리 시작 ===")
            logger.info(f"전체 데이터 크기: {len(data_str)} 문자")
            
            # ME_FD 위치 찾기 (줄바꿈 기준으로 찾기)
            lines = data_str.split('\n')
            me_fd_line_index = -1
            
            for i, line in enumerate(lines):
                if line.startswith('ME_FD:'):
                    me_fd_line_index = i
                    break
            
            if me_fd_line_index == -1:
                logger.error("ME_FD 라인을 찾을 수 없습니다")
                return
            
            logger.info(f"ME_FD 라인 인덱스: {me_fd_line_index}")
            
            # ME_OD 부분 추출 (ME_FD 라인 전까지의 모든 라인)
            me_od_lines = lines[:me_fd_line_index]
            me_od_part = '\n'.join(me_od_lines).strip()
            
            if me_od_part:
                logger.info(f"ME_OD 부분 추출: {len(me_od_part)} 문자")
                logger.debug(f"ME_OD 내용: {me_od_part}")
                
                # 각 ME_OD 라인을 개별적으로 처리
                for line in me_od_lines:
                    if line.strip() and line.startswith('ME_OD:'):
                        logger.debug(f"ME_OD 라인 처리: {line}")
                        self._process_single_message(line)
            
            # ME_FD 부분 추출 (ME_FD 라인부터 끝까지)
            me_fd_lines = lines[me_fd_line_index:]
            me_fd_part = '\n'.join(me_fd_lines).strip()
            
            if me_fd_part:
                logger.info(f"ME_FD 부분 추출: {len(me_fd_part)} 문자")
                logger.debug(f"ME_FD 내용 시작: {me_fd_part[:100]}...")
                
                # ME_FD 부분을 바이너리 데이터로 변환하여 처리
                me_fd_binary_data = me_fd_part.encode('utf-8', errors='ignore')
                self._handle_first_detection_binary_response(me_fd_binary_data)
            
            logger.info(f"=== ME_OD와 ME_FD 혼재 패킷 처리 완료 ===")
            
        except Exception as e:
            logger.error(f"ME_OD와 ME_FD 혼재 패킷 처리 오류: {e}")

    def _process_multiple_me_fd_binary(self, data_str: str):
        """여러 ME_FD가 포함된 바이너리 데이터 처리"""
        try:
            logger.info(f"여러 ME_FD 바이너리 데이터 처리 시작")
            
            # ME_FD 위치들을 모두 찾기
            me_fd_positions = []
            start_pos = 0
            while True:
                pos = data_str.find('ME_FD:', start_pos)
                if pos == -1:
                    break
                me_fd_positions.append(pos)
                start_pos = pos + 1
            
            logger.info(f"발견된 ME_FD 개수: {len(me_fd_positions)}")
            
            # 각 ME_FD를 개별적으로 처리
            for i, me_fd_start in enumerate(me_fd_positions):
                logger.info(f"ME_FD {i+1} 처리 시작 (위치: {me_fd_start})")
                
                # 다음 ME_FD 위치 찾기
                next_me_fd_start = -1
                if i + 1 < len(me_fd_positions):
                    next_me_fd_start = me_fd_positions[i + 1]
                
                # 현재 ME_FD 데이터 추출
                if next_me_fd_start != -1:
                    # 다음 ME_FD가 있는 경우: 현재 ME_FD부터 다음 ME_FD 직전까지
                    me_fd_data = data_str[me_fd_start:next_me_fd_start]
                    logger.info(f"ME_FD {i+1} 데이터 크기: {len(me_fd_data)} bytes")
                else:
                    # 마지막 ME_FD인 경우: 현재 ME_FD부터 끝까지
                    me_fd_data = data_str[me_fd_start:]
                    logger.info(f"마지막 ME_FD 데이터 크기: {len(me_fd_data)} bytes")
                
                # 바이너리 처리
                binary_data = me_fd_data.encode('utf-8', errors='ignore')
                self._handle_first_detection_binary_response(binary_data)
            
        except Exception as e:
            logger.error(f"여러 ME_FD 바이너리 처리 오류: {e}")

    def _process_binary_message(self, message_type: str, data: bytes):
        """바이너리 메시지 처리"""
        try:
            if message_type == 'MR_OD':
                self._handle_object_detail_binary_response(data)
            elif message_type == 'ME_FD':
                self._handle_first_detection_binary_response(data)
            elif message_type == 'LR_OI':
                self._handle_object_image_binary_response(data)
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
            logger.info(f"=== ME_FD 바이너리 데이터 분석 시작 ===")
            logger.info(f"전체 데이터 크기: {len(data)} bytes")
            logger.info(f"데이터 시작 부분: {data[:100]}")
            
            # 텍스트 부분과 이미지 부분 분리  
            text_part = self.binary_processor.extract_text_part_from_binary(data, 'ME_FD')
            if not text_part:
                logger.error("ME_FD: 텍스트 부분 추출 실패")
                return
            
            logger.info(f"추출된 텍스트 부분: '{text_part}'")
            logger.info(f"텍스트 부분 길이: {len(text_part)} 문자")
            
            # 이미지 데이터 추출
            text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
            image_data = data[text_size:]
            logger.info(f"텍스트 크기 (UTF-8 + 콤마): {text_size} bytes")
            logger.info(f"이미지 데이터 크기: {len(image_data)} bytes")
            
            # ME_FD: 프리픽스 제거
            if text_part.startswith('ME_FD:'):
                text_part = text_part[6:]  # 'ME_FD:' 제거
                logger.info(f"프리픽스 제거 후 텍스트: '{text_part}'")
            
            # 여러 객체가 포함되었는지 확인
            if ';' in text_part:
                logger.warning(f"⚠️  ME_FD에서 세미콜론 감지! 여러 객체 가능성: '{text_part}'")
                # 세미콜론으로 분리해서 각 부분 분석
                parts = text_part.split(';')
                logger.info(f"세미콜론으로 분리된 부분들: {len(parts)}개")
                for i, part in enumerate(parts):
                    logger.info(f"  부분 {i+1}: '{part}'")
                    if ',' in part:
                        fields = part.split(',')
                        logger.info(f"    필드 수: {len(fields)}")
                        if len(fields) >= 8:
                            try:
                                image_size = int(fields[7])
                                logger.info(f"    이미지 크기 필드: {image_size}")
                            except:
                                logger.error(f"    이미지 크기 파싱 실패: {fields[7] if len(fields) > 7 else 'N/A'}")
            
            # 터미널에 텍스트 부분 출력 (이미지 제외)
            logger.info(f"ME_FD 텍스트 데이터: {text_part}")
            logger.info(f"ME_FD 이미지 크기: {len(image_data)} bytes")
            logger.info(f"=== ME_FD 바이너리 데이터 분석 완료 ===")
            
            # 텍스트 부분 처리
            self._process_first_detection_with_image(text_part, image_data)

        except Exception as e:
            logger.error(f"ME_FD 바이너리 응답 처리 오류: {e}")

    def _process_first_detection_with_image(self, text_part: str, image_data: bytes):
        """이미지가 포함된 최초 감지 이벤트 처리"""
        
        try:
            # 텍스트 부분에서 객체 정보 파싱
            # 8개 필드: event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size
            # 9개 필드: event_type,object_id,object_type,x_coord,y_coord,area,timestamp,state_info,image_size
            parts = text_part.split(',')
            
            if len(parts) < 8:
                logger.error(f"ME_FD: 필드 수 부족: {len(parts)}")
                return

            # 공통 필드들 (1-7번째)
            event_type = MessageParser._parse_event_type(parts[0])
            object_id = int(parts[1])
            object_type = MessageParser._parse_object_type(parts[2])
            x_coord = float(parts[3])
            y_coord = float(parts[4])
            area = MessageParser._parse_area(parts[5])
            timestamp = MessageParser._parse_timestamp(parts[6])
            
            # 8번째와 9번째 필드 처리
            state_info = None
            if len(parts) == 8:
                # 8개 필드: 8번째가 image_size
                image_size = int(parts[7])
                logger.debug(f"ME_FD (8개 필드): image_size={image_size}")
            elif len(parts) >= 9:
                # 9개 필드: 8번째=state_info, 9번째=image_size
                try:
                    state_info = int(parts[7].strip())
                    logger.debug(f"ME_FD state_info 파싱: {state_info}")
                except ValueError:
                    logger.warning(f"ME_FD state_info 파싱 실패: {parts[7]}")
                
                image_size = int(parts[8])
                logger.debug(f"ME_FD (9개 필드): state_info={state_info}, image_size={image_size}")
            else:
                logger.error(f"ME_FD: 예상치 못한 필드 수: {len(parts)}")
                return

            logger.debug(f"ME_FD 바이너리 파싱 결과: ID={object_id}, Type={object_type.value}, Pos=({x_coord}, {y_coord}), Area={area.value}, EventType={event_type.value if event_type else 'None'}, ImageSize={image_size}, StateInfo={state_info}")

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
                state_info=state_info,
                image_data=image_data
            )

            # 최초 감지 이벤트 시그널 발생
            self.first_object_detected.emit([obj])
            logger.info(f"이미지 포함 최초 감지 이벤트 처리 완료: ID {object_id}, StateInfo={state_info}")

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
            # 1. 먼저 버퍼 전체에서 ME_FD 존재 여부 확인 (우선 처리)
            if 'ME_FD:' in self.message_buffer:
                logger.info(f"🔍 버퍼에서 ME_FD 감지, 바이너리 처리 시작")
                logger.debug(f"버퍼 내용 (처음 200자): {self.message_buffer[:200]}")
                
                # ME_FD 위치들을 모두 찾기
                me_fd_positions = []
                start_pos = 0
                while True:
                    pos = self.message_buffer.find('ME_FD:', start_pos)
                    if pos == -1:
                        break
                    me_fd_positions.append(pos)
                    start_pos = pos + 1
                
                logger.info(f"발견된 ME_FD 개수: {len(me_fd_positions)}")
                
                # 첫 번째 ME_FD 이전 부분이 있다면 먼저 텍스트로 처리
                if me_fd_positions and me_fd_positions[0] > 0:
                    before_first_me_fd = self.message_buffer[:me_fd_positions[0]].strip()
                    logger.info(f"첫 번째 ME_FD 이전 텍스트 처리: {before_first_me_fd[:100]}...")
                    
                    # 이전 부분을 줄바꿈으로 분리하여 처리
                    for line in before_first_me_fd.split('\n'):
                        line = line.strip()
                        if line:
                            self._process_single_message(line)
                
                # 각 ME_FD를 개별적으로 처리
                for i, me_fd_start in enumerate(me_fd_positions):
                    logger.info(f"ME_FD {i+1} 처리 시작 (위치: {me_fd_start})")
                    
                    # 다음 ME_FD 위치 찾기
                    next_me_fd_start = -1
                    if i + 1 < len(me_fd_positions):
                        next_me_fd_start = me_fd_positions[i + 1]
                    
                    # 현재 ME_FD 데이터 추출
                    if next_me_fd_start != -1:
                        # 다음 ME_FD가 있는 경우: 현재 ME_FD부터 다음 ME_FD 직전까지
                        me_fd_data = self.message_buffer[me_fd_start:next_me_fd_start]
                        logger.info(f"ME_FD {i+1} 데이터 크기: {len(me_fd_data)} bytes")
                    else:
                        # 마지막 ME_FD인 경우: 현재 ME_FD부터 끝까지
                        me_fd_data = self.message_buffer[me_fd_start:]
                        logger.info(f"마지막 ME_FD 데이터 크기: {len(me_fd_data)} bytes")
                    
                    # 바이너리 처리
                    binary_data = me_fd_data.encode('utf-8', errors='ignore')
                    self._handle_binary_data(binary_data)
                
                # 버퍼 초기화
                self.message_buffer = ""
                return
            
            # 2. ME_FD가 없는 경우 기존 텍스트 처리 로직
            while '\n' in self.message_buffer:
                line, self.message_buffer = self.message_buffer.split('\n', 1)
                message = line.strip()
                if message:
                    self._process_single_message(message)
                    
        except Exception as e:
            logger.error(f"메시지 버퍼 처리 오류: {e}")
            self.message_buffer = ""  # 오류 시 버퍼 초기화

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
                MessagePrefix.MR_OD: self._handle_object_detail_response,
                MessagePrefix.AR_AC: self._handle_access_control_response,
                MessagePrefix.AR_UA: self._handle_access_control_update_response,
                MessagePrefix.LR_RL: self._handle_pilot_log_response,
                MessagePrefix.LR_OL: self._handle_object_detection_log_response,
                MessagePrefix.LR_BL: self._handle_bird_risk_log_response
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
            logger.debug(f"MR_OD 전체 응답: {data}")
            
            # 응답 성공/실패 여부 확인
            if data.startswith("OK"):
                self._handle_object_detail_success(data)
            elif data.startswith("ERR"):
                self._handle_object_detail_error_response(data)
            else:
                logger.error(f"MR_OD 알 수 없는 응답 형식: {data}")
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

    def _handle_access_control_response(self, data: str):
        """출입 제어 설정 응답 처리 (AR_AC)"""
        try:
            logger.debug(f"AR_AC 응답 수신: {data}")
            settings = MessageInterface.parse_access_control_response(data)
            self.access_control_response.emit(settings)
            logger.info(f"출입 제어 설정 응답 처리 완료: {settings.to_dict()}")
        except Exception as e:
            logger.error(f"출입 제어 설정 응답 처리 실패: {e}")
            self.access_control_error.emit(str(e))

    def _handle_access_control_update_response(self, data: str):
        """출입 제어 설정 업데이트 응답 처리 (AR_UA)"""
        try:
            logger.debug(f"AR_UA 응답 수신: {data}")
            success = MessageInterface.parse_access_control_update_response(data)
            
            if success:
                self.access_control_update_response.emit(True, "설정이 성공적으로 업데이트되었습니다.")
                logger.info("출입 제어 설정 업데이트 성공")
            else:
                error_msg = data if not data.startswith("ERR") else data[4:]  # "ERR," 제거
                self.access_control_update_response.emit(False, error_msg)
                logger.warning(f"출입 제어 설정 업데이트 실패: {error_msg}")
                
        except Exception as e:
            logger.error(f"출입 제어 설정 업데이트 응답 처리 실패: {e}")
            self.access_control_error.emit(str(e))

    def _handle_pilot_log_response(self, data: str):
        """파일럿 로그 응답 처리 (LR_RL) - 개선된 버전"""
        try:
            logger.debug(f"LR_RL 응답 수신: {data[:200]}...")
            logger.debug(f"LR_RL 전체 응답: {data}")
            
            pilot_logs = MessageInterface.parse_pilot_log_response(data)
            self.pilot_log_response.emit(pilot_logs)
            logger.info(f"파일럿 로그 응답 처리 완료: {len(pilot_logs)}건")
        except Exception as e:
            logger.error(f"파일럿 로그 응답 처리 실패: {e}, 데이터: {data[:200]}...")
            self.pilot_log_error.emit(str(e))

    def _handle_object_detection_log_response(self, data: str):
        """객체 감지 로그 응답 처리 (LR_OL) - 개선된 버전"""
        try:
            logger.debug(f"LR_OL 응답 수신: {data[:200]}...")
            logger.debug(f"LR_OL 전체 응답: {data}")
            
            detection_logs = MessageInterface.parse_object_detection_log_response(data)
            self.object_detection_log_response.emit(detection_logs)
            logger.info(f"객체 감지 로그 응답 처리 완료: {len(detection_logs)}건")
        except Exception as e:
            logger.error(f"객체 감지 로그 응답 처리 실패: {e}, 데이터: {data[:200]}...")
            self.object_detection_log_error.emit(str(e))

    def _handle_bird_risk_log_response(self, data: str):
        """조류 위험도 로그 응답 처리 (LR_BL) - 개선된 버전"""
        try:
            logger.debug(f"LR_BL 응답 수신: {data[:200]}...")
            logger.debug(f"LR_BL 전체 응답: {data}")
            
            bird_risk_logs = MessageInterface.parse_bird_risk_log_response(data)
            self.bird_risk_log_response.emit(bird_risk_logs)
            logger.info(f"조류 위험도 로그 응답 처리 완료: {len(bird_risk_logs)}건")
        except Exception as e:
            logger.error(f"조류 위험도 로그 응답 처리 실패: {e}, 데이터: {data[:200]}...")
            self.bird_risk_log_error.emit(str(e))

    def _handle_object_image_binary_response(self, data: bytes):
        """LR_OI 바이너리 응답 처리 (객체 이미지 조회 응답)"""
        try:
            # 텍스트 부분과 이미지 부분 분리
            text_part = self.binary_processor.extract_text_part_from_binary(data, 'LR_OI')
            if not text_part:
                logger.error("LR_OI: 텍스트 부분 추출 실패")
                return
            
            # 이미지 데이터 추출
            text_size = len(text_part.encode('utf-8')) + 1  # 콤마 포함
            image_data = data[text_size:]
            
            logger.info(f"LR_OI 텍스트 데이터: {text_part}")
            logger.info(f"LR_OI 이미지 크기: {len(image_data)} bytes")
            
            # LR_OI: 프리픽스 제거하고 응답 처리
            if text_part.startswith('LR_OI:'):
                text_part = text_part[6:]  # 'LR_OI:' 제거
            
            # 응답 성공/실패 여부 확인
            if text_part.startswith("OK"):
                self._process_object_image_with_data(text_part, image_data)
            elif text_part.startswith("ERR"):
                error_msg = text_part[4:] if len(text_part) > 4 else "알 수 없는 오류"
                logger.warning(f"객체 이미지 조회 오류: {error_msg}")
                # 요청 소스에 따라 다른 에러 시그널 발생
                if self.is_log_page_request:
                    self.log_object_image_error.emit(error_msg)
                else:
                    self.object_detail_error.emit(error_msg)
                # 에러 처리 후 초기화
                self.requested_object_id = None
                self.is_log_page_request = False
            else:
                logger.error(f"LR_OI 알 수 없는 응답 형식: {text_part}")
                # 요청 소스에 따라 다른 에러 시그널 발생
                if self.is_log_page_request:
                    self.log_object_image_error.emit("알 수 없는 응답 형식")
                else:
                    self.object_detail_error.emit("알 수 없는 응답 형식")
                # 에러 처리 후 초기화
                self.requested_object_id = None
                self.is_log_page_request = False

        except Exception as e:
            logger.error(f"LR_OI 바이너리 응답 처리 오류: {e}")
            # 요청 소스에 따라 다른 에러 시그널 발생
            if self.is_log_page_request:
                self.log_object_image_error.emit(str(e))
            else:
                self.object_detail_error.emit(str(e))
            # 에러 처리 후 초기화
            self.requested_object_id = None
            self.is_log_page_request = False

    def _process_object_image_with_data(self, text_part: str, image_data: bytes):
        """LR_OI 객체 이미지 데이터 처리"""
        try:
            # text_part: "OK,image_size"에서 정보 추출
            parts = text_part.split(',')
            if len(parts) < 2:
                logger.error(f"LR_OI 응답 형식 오류: {text_part}")
                return
            
            # OK 확인
            if parts[0] != "OK":
                logger.error(f"LR_OI 응답 실패: {text_part}")
                return
            
            try:
                expected_image_size = int(parts[1])
                actual_image_size = len(image_data)
                
                if expected_image_size != actual_image_size:
                    logger.warning(f"LR_OI 이미지 크기 불일치: 예상={expected_image_size}, 실제={actual_image_size}")
                
                # 요청된 객체 ID 사용 (없으면 0)
                object_id = self.requested_object_id if self.requested_object_id is not None else 0
                
                # DetectedObject 생성 (이미지만 포함)
                # LR_OI는 이미지만 반환하므로 기본값으로 객체 생성
                detected_object = DetectedObject(
                    object_id=object_id,
                    object_type=ObjectType.UNKNOWN,
                    x_coord=0.0,
                    y_coord=0.0,
                    area=AirportArea.TWY_A,
                    event_type=None,
                    timestamp=None,
                    state_info=None,
                    image_data=image_data
                )
                
                # 요청 소스에 따라 다른 시그널 발생
                if self.is_log_page_request:
                    logger.info(f"로그 페이지 객체 이미지 응답: ID={object_id}")
                    self.log_object_image_response.emit(detected_object)
                else:
                    logger.info(f"메인 페이지 객체 상세보기 응답: ID={object_id}")
                    self.object_detail_response.emit(detected_object)
                
                # 요청 완료 후 초기화
                self.requested_object_id = None
                self.is_log_page_request = False
                
            except ValueError as e:
                logger.error(f"LR_OI 이미지 크기 파싱 오류: {e}")
                
        except Exception as e:
            logger.error(f"LR_OI 객체 이미지 데이터 처리 오류: {e}")

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