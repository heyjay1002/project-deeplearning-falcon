from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtNetwork import QTcpSocket
from config.config import TCP_SERVER_IP, TCP_SERVER_PORT, CONNECTION_TIMEOUT

class TcpClient(QObject):
    # 시그널 정의
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    raw_data_received = pyqtSignal(str)  # 원본 텍스트 그대로 전달
    connection_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.connected.connect(self.on_connected)
        self.socket.disconnected.connect(self.on_disconnected)
        self.socket.readyRead.connect(self.on_data_ready)
        self.socket.errorOccurred.connect(self.on_error)
        
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.connect_to_server)
    
    def connect_to_server(self):
        """서버 연결"""
        print(f"서버 연결 시도: {TCP_SERVER_IP}:{TCP_SERVER_PORT}")
        self.socket.connectToHost(TCP_SERVER_IP, TCP_SERVER_PORT)
    
    def disconnect_from_server(self):
        """서버 연결 해제"""
        self.socket.disconnectFromHost()
    
    def send_command(self, command_text):
        """명령어 전송 (CCTV 요청 등)"""
        if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            data = command_text.encode('utf-8')
            self.socket.write(data)
            return True
        return False
    
    def on_connected(self):
        """연결 성공"""
        print("TCP 서버 연결 성공")
        self.reconnect_timer.stop()
        self.connected.emit()
    
    def on_disconnected(self):
        """연결 해제"""
        print("TCP 서버 연결 해제")
        self.disconnected.emit()
        self.start_reconnect()
    
    def on_data_ready(self):
        """데이터 수신 - 파싱하지 않고 그대로 전달"""
        while self.socket.bytesAvailable():
            raw_bytes = self.socket.readAll()
            try:
                # 바이트 -> 문자열 변환만
                raw_text = raw_bytes.data().decode('utf-8')
                
                # 여러 메시지가 한번에 올 수 있으므로 분리
                messages = raw_text.strip().split('\n')
                for msg in messages:
                    if msg.strip():
                        # 파싱 없이 그대로 전달!
                        self.raw_data_received.emit(msg.strip())
                        
            except UnicodeDecodeError as e:
                print(f"텍스트 디코딩 오류: {e}")
    
    def on_error(self, error):
        """연결 오류"""
        error_msg = f"TCP 연결 오류: {self.socket.errorString()}"
        print(error_msg)
        self.connection_error.emit(error_msg)
        self.start_reconnect()
    
    def start_reconnect(self):
        """재연결 시도"""
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start(3000)  # 3초 후 재연결