from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
from config import Settings, Constants, MessagePrefix, BirdRiskLevel, RunwayRiskLevel
from .interface import MessageInterface
from models.detected_object import DetectedObject
from .logger import logger
from .udp_client import UdpClient

class TcpClient(QObject):
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
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.connected.connect(self.on_connected)
        self.socket.disconnected.connect(self.on_disconnected)
        self.socket.readyRead.connect(self.on_data_ready)
        self.socket.errorOccurred.connect(self.on_error)
        
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.connect_to_server)
        
        self.message_interface = MessageInterface()
        self.settings = Settings.get_instance()
        
        # UDP 클라이언트 초기화
        self.udp_client = UdpClient()
        
        # 메시지 버퍼링을 위한 변수
        self.message_buffer = ""
        self.is_connecting = False
    
    def connect_to_server(self):
        """서버 연결"""
        if self.is_connecting or self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            return
            
        self.is_connecting = True
        logger.info(f"서버 연결 시도: {self.settings.server.tcp_ip}:{self.settings.server.tcp_port}")
        
        self.socket.connectToHost(
            self.settings.server.tcp_ip, 
            self.settings.server.tcp_port
        )
        
        # 타임아웃 설정
        if not self.socket.waitForConnected(self.settings.server.connection_timeout * 1000):
            self.is_connecting = False
            self.on_error(self.socket.error())
    
    def disconnect_from_server(self):
        """서버 연결 해제"""
        self.reconnect_timer.stop()
        if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            logger.info("서버 연결 해제")
            self.socket.disconnectFromHost()
        # UDP 클라이언트도 연결 해제
        if self.udp_client.is_running:
            self.udp_client.disconnect()
    
    def send_command(self, command_text: str) -> bool:
        """명령어 전송"""
        if not self.is_connected():
            logger.error(f"연결되지 않은 상태에서 명령 전송 실패: {command_text}")
            return False
            
        try:
            data = (command_text + '\n').encode('utf-8')
            bytes_written = self.socket.write(data)
            if bytes_written == -1:
                logger.error(f"명령 전송 실패: {command_text}")
                return False
            logger.debug(f"명령 전송 성공: {command_text}")
            return True
        except Exception as e:
            logger.error(f"명령 전송 중 오류: {e}")
            return False
    
    def request_cctv_a(self) -> bool:
        """CCTV A 영상 요청"""
        try:
            command = MessageInterface.create_cctv_request("A")
            return self.send_command(command)
        except Exception as e:
            print(f"CCTV A 요청 생성 오류: {e}")
            return False
    
    def request_cctv_b(self) -> bool:
        """CCTV B 영상 요청"""
        try:
            command = MessageInterface.create_cctv_request("B")
            return self.send_command(command)
        except Exception as e:
            print(f"CCTV B 요청 생성 오류: {e}")
            return False
    
    def request_map(self) -> bool:
        """지도 영상 요청"""
        try:
            command = MessageInterface.create_map_request()
            return self.send_command(command)
        except Exception as e:
            print(f"지도 요청 생성 오류: {e}")
            return False
    
    def request_object_detail(self, object_id: int) -> bool:
        """객체 상세보기 요청"""
        try:
            command = MessageInterface.create_object_detail_request(object_id)
            return self.send_command(command)
        except Exception as e:
            print(f"객체 상세보기 요청 생성 오류: {e}")
            return False
    
    def on_connected(self):
        """연결 성공"""
        logger.info("TCP 서버 연결 성공")
        self.is_connecting = False
        self.reconnect_timer.stop()
        self.message_buffer = ""  # 버퍼 초기화
        self.connected.emit()
    
    def on_disconnected(self):
        """연결 해제"""
        logger.info("TCP 서버 연결 해제")
        self.is_connecting = False
        self.disconnected.emit()
        self.start_reconnect()
    
    def on_data_ready(self):
        """데이터 수신 및 처리 - 개선된 버퍼링"""
        while self.socket.bytesAvailable():
            raw_bytes = self.socket.readAll()
            try:
                raw_text = raw_bytes.data().decode('utf-8')
                self.message_buffer += raw_text
                
                # 완전한 메시지들만 처리 (개행 문자 기준)
                while '\n' in self.message_buffer:
                    line, self.message_buffer = self.message_buffer.split('\n', 1)
                    message = line.strip()
                    if message:
                        self.process_message(message)
                        
            except UnicodeDecodeError as e:
                logger.error(f"텍스트 디코딩 오류: {e}")
                # 잘못된 데이터는 버퍼에서 제거
                self.message_buffer = ""
    
    def process_message(self, message: str):
        """메시지 처리"""
        try:
            prefix, data = MessageInterface.parse_message(message)
            logger.debug(f"수신 메시지 - {prefix.value}: {data}")
            
            if prefix == MessagePrefix.ME_OD:
                # 객체 감지 이벤트
                objects = MessageInterface.parse_object_detection_event(data)
                self.object_detected.emit(objects)
                
            elif prefix == MessagePrefix.ME_BR:
                # 조류 위험도 변경 이벤트
                risk_level = MessageInterface.parse_bird_risk_level_event(data)
                self.bird_risk_changed.emit(risk_level)
                
            elif prefix == MessagePrefix.ME_RA:
                # 활주로 A 위험도 변경 이벤트
                risk_level = MessageInterface.parse_runway_risk_level_event(data)
                self.runway_a_risk_changed.emit(risk_level)
                
            elif prefix == MessagePrefix.ME_RB:
                # 활주로 B 위험도 변경 이벤트
                risk_level = MessageInterface.parse_runway_risk_level_event(data)
                self.runway_b_risk_changed.emit(risk_level)
                
            elif prefix == MessagePrefix.MR_CA:
                # CCTV A 응답
                self.cctv_a_response.emit(data)
                # UDP 스트리밍 시작
                if not self.udp_client.is_running:
                    self.udp_client.connect()
                
            elif prefix == MessagePrefix.MR_CB:
                # CCTV B 응답
                self.cctv_b_response.emit(data)
                # UDP 스트리밍 시작
                if not self.udp_client.is_running:
                    self.udp_client.connect()
                
            elif prefix == MessagePrefix.MR_MP:
                # 지도 응답
                self.map_response.emit(data)
                
            elif prefix == MessagePrefix.MR_OD:
                # 객체 상세보기 응답
                self.process_object_detail_response(data)
                
            else:
                logger.warning(f"알 수 없는 메시지 타입: {prefix}")
                
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
            logger.error(f"원본 메시지: {message}")
    
    def process_object_detail_response(self, data: str):
        """객체 상세보기 응답 처리"""
        try:
            if data.startswith("OK"):
                # OK:object_info 형식
                if Constants.MESSAGE_SEPARATOR in data:
                    _, object_info_str = data.split(Constants.MESSAGE_SEPARATOR, 1)
                    obj_info = MessageInterface.parse_object_info(object_info_str, include_image=True)
                    self.object_detail_response.emit(obj_info)
                else:
                    raise ValueError("Invalid OK response format")
            elif data.startswith("ERR"):
                # ERR:error_message 형식
                if Constants.MESSAGE_SEPARATOR in data:
                    _, error_msg = data.split(Constants.MESSAGE_SEPARATOR, 1)
                    logger.error(f"객체 상세보기 오류: {error_msg}")
                    self.object_detail_error.emit(error_msg)
                else:
                    error_msg = "Unknown error"
                    logger.error(f"객체 상세보기 오류: {error_msg}")
                    self.object_detail_error.emit(error_msg)
            else:
                raise ValueError(f"Unknown response format: {data}")
                
        except Exception as e:
            error_msg = f"객체 상세보기 응답 처리 오류: {e}"
            logger.error(error_msg)
            self.object_detail_error.emit(error_msg)
    
    def on_error(self, error):
        """연결 오류"""
        error_msg = f"TCP 연결 오류: {self.socket.errorString()}"
        logger.error(error_msg)
        self.is_connecting = False
        self.connection_error.emit(error_msg)
        self.start_reconnect()
    
    def start_reconnect(self):
        """재연결 시도"""
        if not self.reconnect_timer.isActive() and not self.is_connecting:
            logger.info(f"{self.settings.server.reconnect_interval}초 후 재연결 시도")
            self.reconnect_timer.start(self.settings.server.reconnect_interval * 1000)
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.socket.state() == QTcpSocket.SocketState.ConnectedState
    
    def get_connection_state(self) -> str:
        """현재 연결 상태 반환"""
        state = self.socket.state()
        if state == QTcpSocket.SocketState.ConnectedState:
            return "연결됨"
        elif state == QTcpSocket.SocketState.ConnectingState:
            return "연결 중"
        elif state == QTcpSocket.SocketState.UnconnectedState:
            return "연결 안됨"
        else:
            return "알 수 없음"