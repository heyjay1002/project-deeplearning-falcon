"""
TCP 통신을 위한 기본 클래스들
"""

import socket
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import threading
from config import *


class TCPBase(ABC):
    """TCP 통신을 위한 기본 클래스"""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.buffer = ""
    
    def _init_socket(self) -> None:
        """소켓 초기화"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setblocking(False)
        except Exception as e:
            print(f"[ERROR] TCP 소켓 초기화 실패: {e}")
            raise
    
    def close(self) -> None:
        """소켓 종료"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"[WARNING] TCP 소켓 종료 중 오류: {e}")
        self.socket = None
        self.buffer = ""


class TCPServer(TCPBase):
    """JSON 데이터 수신용 TCP 서버"""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0):
        super().__init__(host, port)
        self.client_sockets = set()
    
    def start(self) -> None:
        """서버 시작"""
        self._init_socket()
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True
        print(f"[INFO] TCP 서버 시작 (포트: {self.port})")
    
    def accept_client(self) -> bool:
        """새로운 클라이언트 연결 수락"""
        try:
            client_socket, addr = self.socket.accept()
            client_socket.setblocking(False)
            self.client_sockets.add(client_socket)
            print(f"[TCP:{self.port}] 클라이언트 연결됨: {addr[0]}:{addr[1]}")
            return True
        except BlockingIOError:
            return False
        except Exception as e:
            if self.running:
                print(f"[ERROR] 클라이언트 연결 수락 실패: {e}")
            return False
    
    def _cleanup_disconnected_clients(self, disconnected: set) -> None:
        """연결 종료된 클라이언트 정리"""
        for client_socket in disconnected:
            try:
                client_socket.close()
                self.client_sockets.discard(client_socket)
                print("[INFO] 클라이언트 연결 종료")
            except Exception as e:
                print(f"[WARNING] 클라이언트 소켓 정리 중 오류: {e}")
    
    def receive_json(self) -> List[Dict[str, Any]]:
        """모든 클라이언트로부터 JSON 데이터 수신"""
        received_data = []
        disconnected = set()
        
        for client_socket in list(self.client_sockets):
            try:
                data = client_socket.recv(TCP_BUFFER_SIZE)
                if not data:
                    disconnected.add(client_socket)
                    continue
                
                # 데이터 처리
                self.buffer += data.decode('utf-8')
                
                # JSON 파싱 (여러 메시지 처리)
                while '\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\n', 1)
                    if message.strip():  # 빈 메시지 무시
                        try:
                            json_data = json.loads(message)
                            received_data.append(json_data)
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] JSON 파싱 실패: {e} - 메시지: {message}")
                
            except BlockingIOError:
                continue
            except (UnicodeDecodeError, ConnectionResetError) as e:
                print(f"[ERROR] 클라이언트 연결 오류: {e}")
                disconnected.add(client_socket)
            except Exception as e:
                print(f"[ERROR] 데이터 수신 중 오류: {e}")
                disconnected.add(client_socket)
        
        self._cleanup_disconnected_clients(disconnected)
        return received_data
    
    def receive_binary(self) -> bytes:
        """바이너리 데이터 수신 (첫 번째 클라이언트에서만)"""
        disconnected = set()
        
        for client_socket in list(self.client_sockets):
            try:
                data = client_socket.recv(TCP_BUFFER_SIZE)
                if not data:
                    disconnected.add(client_socket)
                    continue
                
                self._cleanup_disconnected_clients(disconnected)
                return data
                
            except BlockingIOError:
                continue
            except Exception as e:
                print(f"[ERROR] 바이너리 데이터 수신 중 오류: {e}")
                disconnected.add(client_socket)
        
        self._cleanup_disconnected_clients(disconnected)
        return b''
    
    def send_to_client(self, data: Dict[str, Any]) -> None:
        """모든 클라이언트에게 JSON 데이터 전송"""
        if not self.client_sockets:
            return
        
        disconnected = set()
        try:
            json_str = json.dumps(data, ensure_ascii=False) + '\n'
            encoded_data = json_str.encode('utf-8')
        except (TypeError, ValueError) as e:
            print(f"[ERROR] JSON 직렬화 실패: {e}")
            return
        
        for client_socket in list(self.client_sockets):
            try:
                client_socket.send(encoded_data)
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"[ERROR] 클라이언트 전송 실패 (연결 끊김): {e}")
                disconnected.add(client_socket)
            except Exception as e:
                print(f"[ERROR] 클라이언트 전송 실패: {e}")
                disconnected.add(client_socket)
        
        self._cleanup_disconnected_clients(disconnected)
    
    def send_binary_to_client(self, data: bytes) -> None:
        """모든 클라이언트에게 바이너리 데이터 전송"""
        if not self.client_sockets:
            return
        
        disconnected = set()
        
        for client_socket in list(self.client_sockets):
            try:
                client_socket.send(data)
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"[ERROR] 클라이언트 바이너리 전송 실패 (연결 끊김): {e}")
                disconnected.add(client_socket)
            except Exception as e:
                print(f"[ERROR] 클라이언트 바이너리 전송 실패: {e}")
                disconnected.add(client_socket)
        
        self._cleanup_disconnected_clients(disconnected)


class TCPClient(TCPBase):
    """JSON 데이터 송신용 TCP 클라이언트"""
    
    def start(self) -> bool:
        """서버 연결"""
        try:
            self._init_socket()
            
            # 연결 시도 시에는 blocking 모드 사용
            self.socket.setblocking(True)
            self.socket.settimeout(5.0)  # 5초 타임아웃 설정
            
            print(f"[INFO] TCP 서버 연결 시도 중... (서버: {self.host}:{self.port})")
            self.socket.connect((self.host, self.port))
            
            # 연결 성공 후 non-blocking 모드로 전환
            self.socket.setblocking(False)
            self.socket.settimeout(None)
            self.running = True
            print(f"[INFO] TCP 서버 연결 성공 (서버: {self.host}:{self.port})")
            return True
            
        except ConnectionRefusedError:
            print(f"[ERROR] TCP 서버 연결 거부됨 (서버: {self.host}:{self.port})")
            self.close()
            return False
        except socket.timeout:
            print(f"[ERROR] TCP 서버 연결 타임아웃 (서버: {self.host}:{self.port})")
            self.close()
            return False
        except Exception as e:
            print(f"[ERROR] TCP 서버 연결 실패: {e}")
            self.close()
            return False
    
    def send_message_json(self, data: Dict[str, Any]) -> bool:
        """JSON 데이터 전송"""
        if not self.running or not self.socket:
            return False
            
        try:
            json_str = json.dumps(data, ensure_ascii=False) + '\n'
            encoded_data = json_str.encode('utf-8')
            self.socket.send(encoded_data)
            return True
        except (TypeError, ValueError) as e:
            print(f"[ERROR] JSON 직렬화 실패: {e}")
            return False
        except (ConnectionResetError, BrokenPipeError) as e:
            if self.running:
                print(f"[ERROR] 연결이 끊어짐: {e}")
                self.close()
            return False
        except Exception as e:
            if self.running:
                print(f"[ERROR] 데이터 전송 오류: {e}")
            return False
    
    def send_message_binary(self, data: bytes) -> bool:
        """바이너리 데이터 전송"""
        if not self.running or not self.socket:
            return False
            
        try:
            self.socket.send(data)
            return True
        except (ConnectionResetError, BrokenPipeError) as e:
            if self.running:
                print(f"[ERROR] 연결이 끊어짐: {e}")
                self.close()
            return False
        except Exception as e:
            if self.running:
                print(f"[ERROR] 바이너리 데이터 전송 오류: {e}")
            return False
    
    def receive_json(self) -> Optional[Dict[str, Any]]:
        """JSON 데이터 수신"""
        if not self.running or not self.socket:
            return None
            
        try:
            data = self.socket.recv(TCP_BUFFER_SIZE)
            if not data:
                return None
            
            # 데이터 처리
            self.buffer += data.decode('utf-8')
            
            # JSON 파싱
            if '\n' in self.buffer:
                message, self.buffer = self.buffer.split('\n', 1)
                if message.strip():  # 빈 메시지 무시
                    try:
                        return json.loads(message)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON 파싱 실패: {e} - 메시지: {message}")
                        return None
                        
        except BlockingIOError:
            return None
        except (UnicodeDecodeError, ConnectionResetError) as e:
            if self.running:
                print(f"[ERROR] 연결 오류: {e}")
                self.close()
            return None
        except Exception as e:
            if self.running:
                print(f"[ERROR] 데이터 수신 중 오류: {e}")
            return None
    
    def receive_binary(self) -> bytes:
        """바이너리 데이터 수신"""
        if not self.running or not self.socket:
            return b''
            
        try:
            data = self.socket.recv(TCP_BUFFER_SIZE)
            if not data:
                return b''
            return data
            
        except BlockingIOError:
            return b''
        except (ConnectionResetError, BrokenPipeError) as e:
            if self.running:
                print(f"[ERROR] 연결 오류: {e}")
                self.close()
            return b''
        except Exception as e:
            if self.running:
                print(f"[ERROR] 바이너리 데이터 수신 중 오류: {e}")
            return b''