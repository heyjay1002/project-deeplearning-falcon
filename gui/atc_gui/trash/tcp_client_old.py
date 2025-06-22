from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
from config import Settings, Constants, MessagePrefix, BirdRiskLevel, RunwayRiskLevel
from .interface_old import MessageInterface
from models.detected_object import DetectedObject
from .logger import logger
from models.bird_runway_risk import BirdRisk, RunwayRisk



class TcpClient(QObject):
    """TCP 클라이언트 - 서버와의 통신을 담당"""
    
    # === 시그널 정의 ===
    # 연결 상태 시그널
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    
    # 이벤트 시그널
    object_detected = pyqtSignal(list)  # DetectedObject 리스트
    bird_risk_changed = pyqtSignal(BirdRiskLevel)
    runway_a_risk_changed = pyqtSignal(RunwayRiskLevel)
    runway_b_risk_changed = pyqtSignal(RunwayRiskLevel)
    
    # 응답 시그널
    cctv_a_response = pyqtSignal(str)
    cctv_b_response = pyqtSignal(str)
    map_response = pyqtSignal(str)
    object_detail_response = pyqtSignal(DetectedObject)
    object_detail_error = pyqtSignal(str)

    def __init__(self):
        """초기화"""
        super().__init__()
        
        # 설정 및 인터페이스
        self.settings = Settings.get_instance()
        self.message_interface = MessageInterface()
        
        # TCP 소켓 및 연결 관리
        self.socket = QTcpSocket(self)
        self._setup_socket_signals()
        
        # 연결 타임아웃 타이머
        self.connection_timeout_timer = QTimer(self)
        self.connection_timeout_timer.setSingleShot(True)
        self.connection_timeout_timer.timeout.connect(self._on_connection_timeout)
        
        # 상태 관리
        self.message_buffer = ""
        self.connection_attempts = 0

    def connect_to_server(self) -> bool:
        """서버에 연결 시도"""
        if self.is_connected():
            return True
            
        if self.socket.state() == QTcpSocket.SocketState.ConnectingState:
            return False
            
        logger.info(f"TCP 서버 연결 시도: {self.settings.server.tcp_ip}:{self.settings.server.tcp_port}")
        
        try:
            # 이전 연결 시도가 있다면 중단
            if self.socket.state() != QTcpSocket.SocketState.UnconnectedState:
                self.socket.abort()
                self.socket.waitForDisconnected(1000)
            
            # 연결 타임아웃 설정
            self._start_connection_timeout()
            
            # 호스트 연결 시도
            self.socket.connectToHost(
                self.settings.server.tcp_ip,
                self.settings.server.tcp_port
            )
            
            # 연결 성공 대기
            if not self.socket.waitForConnected(3000):  # 3초 대기
                return False
                
            return self.is_connected()
            
        except Exception as e:
            self._handle_connection_error(f"연결 시도 중 오류: {e}")
            return False

    def disconnect_from_server(self):
        """서버 연결 해제"""
        logger.info("서버 연결 해제 중...")
        
        # 연결 타임아웃 타이머 중지
        self.connection_timeout_timer.stop()
        
        # TCP 소켓 연결 해제
        if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            self.socket.disconnectFromHost()
            if not self.socket.waitForDisconnected(3000):
                logger.warning("정상적인 연결 해제 실패, 강제 종료")

    def is_connected(self) -> bool:
        """TCP 연결 상태 확인"""
        return self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState

    def get_connection_state(self) -> str:
        """현재 연결 상태 문자열 반환"""
        state_map = {
            QTcpSocket.SocketState.ConnectedState: "연결됨",
            QTcpSocket.SocketState.ConnectingState: "연결 중",
            QTcpSocket.SocketState.UnconnectedState: "연결 안됨",
            QTcpSocket.SocketState.HostLookupState: "호스트 조회 중",
            QTcpSocket.SocketState.ClosingState: "연결 종료 중"
        }
        return state_map.get(self.socket.state(), "알 수 없음")

    # === 요청 메서드 ===
    def request_cctv_a(self) -> bool:
        """CCTV A 영상 요청"""
        return self._send_request(
            MessageInterface.create_cctv_request, 
            "A", 
            "CCTV A 요청"
        )

    def request_cctv_b(self) -> bool:
        """CCTV B 영상 요청"""
        return self._send_request(
            MessageInterface.create_cctv_request, 
            "B", 
            "CCTV B 요청"
        )

    def request_map(self) -> bool:
        """지도 영상 요청"""
        return self._send_request(
            MessageInterface.create_map_request, 
            None, 
            "지도 요청"
        )

    def request_object_detail(self, object_id: int) -> bool:
        """객체 상세보기 요청"""
        return self._send_request(
            MessageInterface.create_object_detail_request, 
            object_id, 
            f"객체 상세보기 요청 (ID: {object_id})"
        )

    # === 소켓 이벤트 핸들러 ===
    def _on_connected(self):
        """연결 성공 처리"""
        logger.info(f"TCP 서버 연결 성공: {self.settings.server.tcp_ip}:{self.settings.server.tcp_port}")
        
        # 연결 타임아웃 타이머 중지
        self.connection_timeout_timer.stop()
        
        self.message_buffer = ""
        self.connected.emit()

    def _on_disconnected(self):
        """연결 해제 처리"""
        logger.info("TCP 서버 연결이 해제되었습니다")
        
        # 연결 타임아웃 타이머 중지
        self.connection_timeout_timer.stop()
        
        self.disconnected.emit()

    def _on_data_ready(self):
        """데이터 수신 처리"""
        try:
            while self.socket.bytesAvailable():
                raw_data = self.socket.readAll().data()
                text_data = raw_data.decode('utf-8')
                self.message_buffer += text_data
                
                # 완전한 메시지들 처리 (개행 문자 기준)
                self._process_buffered_messages()
                
        except UnicodeDecodeError as e:
            logger.error(f"데이터 디코딩 오류: {e}")
            self.message_buffer = ""  # 손상된 버퍼 초기화
        except Exception as e:
            logger.error(f"데이터 수신 처리 오류: {e}")

    def _on_socket_error(self, error):
        """소켓 오류 처리"""
        # 연결 타임아웃 타이머 중지
        self.connection_timeout_timer.stop()
        
        error_msg = f"소켓 오류 ({error}): {self.socket.errorString()}"
        self._handle_connection_error(error_msg)

    def _on_connection_timeout(self):
        """연결 타임아웃 처리"""
        logger.warning(f"연결 타임아웃 ({self.settings.server.connection_timeout}초)")
        
        # 연결 시도 중단 및 소켓 초기화
        if self.socket.state() == QTcpSocket.SocketState.ConnectingState:
            self.socket.abort()
            self.socket.waitForDisconnected(1000)
            
        # 소켓 재초기화
        self.socket = QTcpSocket(self)
        self._setup_socket_signals()
            
        self._handle_connection_error("연결 타임아웃")

    # === 메시지 처리 메서드 ===
    def _process_buffered_messages(self):
        """버퍼된 메시지들을 처리"""
        while '\n' in self.message_buffer:
            line, self.message_buffer = self.message_buffer.split('\n', 1)
            message = line.strip()
            if message:
                self._process_single_message(message)

    def _process_single_message(self, message: str):
        """단일 메시지 처리"""
        try:
            prefix, data = MessageInterface.parse_message(message)
            logger.debug(f"수신 메시지 - {prefix.value}: {data}")
            
            # 메시지 타입별 처리
            handler_map = {
                MessagePrefix.ME_OD: self._handle_object_detection,
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
                logger.warning(f"처리되지 않은 메시지 타입: {prefix.value}")
                
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")

    def _handle_connection_error(self, error_msg: str):
        """연결 오류 처리"""
        logger.error(error_msg)
        self.connection_error.emit(error_msg)

    def _start_connection_timeout(self):
        """연결 타임아웃 타이머 시작"""
        self.connection_timeout_timer.start(self.settings.server.connection_timeout * 1000)

    def _setup_socket_signals(self):
        """소켓 시그널 연결"""
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.readyRead.connect(self._on_data_ready)
        self.socket.errorOccurred.connect(self._on_socket_error)

    def _send_request(self, create_func, param, description: str) -> bool:
        """요청 메시지 전송"""
        if not self.is_connected():
            logger.error("서버에 연결되어 있지 않습니다")
            return False
            
        try:
            message = create_func(param) if param is not None else create_func()
            return self._send_command(message, description)
        except Exception as e:
            logger.error(f"{description} 메시지 생성 중 오류: {e}")
            return False

    def _send_command(self, command: str, description: str) -> bool:
        """명령어 전송"""
        try:
            data = (command + '\n').encode('utf-8')
            bytes_written = self.socket.write(data)
            
            if bytes_written == len(data):
                logger.debug(f"{description} 전송 성공")
                return True
            else:
                logger.error(f"{description} 전송 실패 (부분 전송)")
                return False
                
        except Exception as e:
            logger.error(f"{description} 전송 중 오류: {e}")
            return False

    # === 개별 메시지 핸들러 ===
    def _handle_object_detection(self, data: str):
        """객체 감지 이벤트 처리"""
        objects = MessageInterface.parse_object_detection_event(data)
        self.object_detected.emit(objects)

    def _handle_bird_risk_change(self, data: str):
        """조류 위험도 변경 이벤트 처리"""
        risk_level = MessageInterface.parse_bird_risk_level_event(data)
        self.bird_risk_changed.emit(risk_level)

    def _handle_runway_a_risk_change(self, data: str):
        """활주로 A 위험도 변경 이벤트 처리"""
        risk_level = MessageInterface.parse_runway_risk_level_event(data)
        self.runway_a_risk_changed.emit(risk_level)

    def _handle_runway_b_risk_change(self, data: str):
        """활주로 B 위험도 변경 이벤트 처리"""
        risk_level = MessageInterface.parse_runway_risk_level_event(data)
        self.runway_b_risk_changed.emit(risk_level)

    def _handle_cctv_a_response(self, data: str):
        """CCTV A 응답 처리"""
        logger.info(f"CCTV A 응답 수신: {data}")
        self.cctv_a_response.emit(data)

    def _handle_cctv_b_response(self, data: str):
        """CCTV B 응답 처리"""
        logger.info(f"CCTV B 응답 수신: {data}")
        self.cctv_b_response.emit(data)

    def _handle_map_response(self, data: str):
        """지도 응답 처리"""
        self.map_response.emit(data)

    def _handle_object_detail_response(self, data: str):
        """객체 상세보기 응답 처리"""
        try:
            if data.startswith("OK"):
                self._handle_object_detail_success(data)
            elif data.startswith("ERR"):
                self._handle_object_detail_error(data)
            else:
                raise ValueError(f"알 수 없는 응답 형식: {data}")
                
        except Exception as e:
            error_msg = f"객체 상세보기 응답 처리 오류: {e}"
            logger.error(error_msg)
            self.object_detail_error.emit(error_msg)

    def _handle_object_detail_success(self, data: str):
        """객체 상세보기 성공 응답 처리"""
        if Constants.Protocol.MESSAGE_SEPARATOR not in data:
            raise ValueError("잘못된 OK 응답 형식")
            
        _, object_info_str = data.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
        obj_info = MessageInterface.parse_object_info(object_info_str, include_image=True)
        self.object_detail_response.emit(obj_info)

    def _handle_object_detail_error(self, data: str):
        """객체 상세보기 오류 응답 처리"""
        if Constants.Protocol.MESSAGE_SEPARATOR in data:
            _, error_msg = data.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
        else:
            error_msg = "알 수 없는 오류"
            
        logger.error(f"객체 상세보기 오류: {error_msg}")
        self.object_detail_error.emit(error_msg)