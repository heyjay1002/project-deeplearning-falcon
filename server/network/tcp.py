"""
TCP 통신을 위한 기본 클래스들
"""

import socket
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import time
import threading
import queue
import sys
import os
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
            print(f"[INFO] 클라이언트 연결됨: {addr}")
            return True
        except BlockingIOError:
            return False
        except Exception as e:
            if self.running:
                print(f"[ERROR] 클라이언트 연결 수락 실패: {e}")
            return False
    
    def receive_data(self) -> List[Dict[str, Any]]:
        """모든 클라이언트로부터 JSON 데이터 수신"""
        received_data = []
        disconnected = set()
        
        for client_socket in self.client_sockets:
            try:
                try:
                    data = client_socket.recv(TCP_BUFFER_SIZE)
                    if not data:
                        disconnected.add(client_socket)
                        continue
                    
                    # 데이터 처리
                    self.buffer += data.decode()
                    
                    # JSON 파싱
                    while '\n' in self.buffer:
                        message, self.buffer = self.buffer.split('\n', 1)
                        try:
                            json_data = json.loads(message)
                            received_data.append(json_data)
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] JSON 파싱 실패: {e}")
                            self.buffer = ""
                    
                except BlockingIOError:
                    continue
                except Exception as e:
                    print(f"[ERROR] 데이터 수신 중 오류: {e}")
                    disconnected.add(client_socket)
                    
            except Exception as e:
                print(f"[ERROR] 클라이언트 처리 중 오류: {e}")
                disconnected.add(client_socket)
        
        # 연결 종료된 클라이언트 정리
        for client_socket in disconnected:
            try:
                client_socket.close()
                self.client_sockets.remove(client_socket)
                print("[INFO] 클라이언트 연결 종료")
            except Exception as e:
                print(f"[WARNING] 클라이언트 소켓 정리 중 오류: {e}")
        
        return received_data

    def send_to_client(self, data: Dict[str, Any]) -> None:
        """모든 클라이언트에게 JSON 데이터 전송"""
        if not self.client_sockets:
            return
            
        disconnected = set()
        json_str = json.dumps(data) + '\n'
        encoded_data = json_str.encode()
        
        for client_socket in self.client_sockets:
            try:
                client_socket.send(encoded_data)
            except Exception as e:
                print(f"[ERROR] 클라이언트 전송 실패: {e}")
                disconnected.add(client_socket)
        
        # 연결 종료된 클라이언트 정리
        for client_socket in disconnected:
            try:
                client_socket.close()
                self.client_sockets.remove(client_socket)
                print("[INFO] 클라이언트 연결 종료")
            except Exception as e:
                print(f"[WARNING] 클라이언트 소켓 정리 중 오류: {e}")

class TCPClient(TCPBase):
    """JSON 데이터 송신용 TCP 클라이언트"""
    def start(self) -> bool:
        """서버 연결"""
        try:
            self._init_socket()
            
            # 연결 시도 시에는 blocking 모드 사용
            self.socket.setblocking(True)
            
            # 연결 시도
            print(f"[INFO] TCP 서버 연결 시도 중... (서버: {self.host}:{self.port})")
            self.socket.connect((self.host, self.port))
            
            # 연결 성공 후 non-blocking 모드로 전환
            self.socket.setblocking(False)
            self.running = True
            print(f"[INFO] TCP 서버 연결 성공 (서버: {self.host}:{self.port})")
            return True
            
        except ConnectionRefusedError:
            print(f"[ERROR] TCP 서버 연결 거부됨 (서버: {self.host}:{self.port})")
            self.close()
            return False
        except Exception as e:
            print(f"[ERROR] TCP 서버 연결 실패: {e}")
            self.close()
            return False
    
    def send_data(self, data: Dict[str, Any]) -> bool:
        """JSON 데이터 전송"""
        try:
            json_str = json.dumps(data) + '\n'
            self.socket.send(json_str.encode())
            return True
        except Exception as e:
            if self.running:
                print(f"[ERROR] 데이터 전송 오류: {e}")
            return False

    def receive_data(self) -> Optional[Dict[str, Any]]:
        """JSON 데이터 수신"""
        try:
            # 데이터 수신 시도
            try:
                data = self.socket.recv(TCP_BUFFER_SIZE)
                if not data:
                    return None
                
                # 데이터 처리
                self.buffer += data.decode()
                
                # JSON 파싱
                if '\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\n', 1)
                    try:
                        return json.loads(message)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON 파싱 실패: {e}")
                        self.buffer = ""
                        return None
                
            except BlockingIOError:
                return None
                
        except Exception as e:
            if self.running:
                print(f"[ERROR] 데이터 수신 중 오류: {e}")
            return None 