"""
UDP 통신을 위한 기본 클래스들
"""

import socket
import cv2
import numpy as np
import time
import threading
import sys
import os
from typing import Optional, Tuple, Dict
from abc import ABC, abstractmethod

# 상대 경로 임포트를 절대 경로로 변경
from config import *

class UDPBase(ABC):
    """UDP 통신을 위한 기본 클래스"""
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
    
    def _init_socket(self) -> None:
        """소켓 초기화"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, UDP_BUFFER_SIZE)
            self.socket.setblocking(False)
        except Exception as e:
            print(f"[ERROR] UDP 소켓 초기화 실패: {e}")
            raise
    
    def close(self) -> None:
        """소켓 종료"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"[WARNING] UDP 소켓 종료 중 오류: {e}")
        self.socket = None

class UDPVideoReceiver(UDPBase):
    """시퀀스 번호가 있는 비디오 수신용 클래스"""
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0):
        super().__init__(host, port)
        self.last_seq = -1
    
    def start(self) -> None:
        """수신 시작"""
        self._init_socket()
        self.socket.bind((self.host, self.port))
        self.running = True
        print(f"[INFO] UDP 비디오 수신 시작 (포트: {self.port})")
    
    def receive_frame(self) -> Tuple[Optional[np.ndarray], int]:
        """프레임 수신
        Returns:
            tuple: (프레임, 이미지 번호) 또는 (None, -1)
        """
        try:
            data, _ = self.socket.recvfrom(UDP_BUFFER_SIZE)
            
            # 시퀀스 번호 파싱
            sep_idx = data.find(b':')
            if sep_idx == -1:
                return None, -1
            
            img_num = int(data[:sep_idx])
            if img_num <= self.last_seq:
                return None, -1
            self.last_seq = img_num
            
            # 프레임 디코딩
            frame_arr = np.frombuffer(data[sep_idx+1:], dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            return frame, img_num
            
        except BlockingIOError:
            return None, -1
        except Exception as e:
            if self.running:
                print(f"[ERROR] 프레임 수신 오류: {e}")
            return None, -1

class UDPVideoSender(UDPBase):
    """비디오 송신용 클래스"""
    def __init__(self, host: str = DEFAULT_CLIENT_HOST, port: int = 0):
        super().__init__(host, port)
    
    def start(self) -> None:
        """송신 시작"""
        self._init_socket()
        # 송신 버퍼 크기 설정
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.running = True
        print(f"[INFO] UDP 비디오 송신 시작 (대상: {self.host}:{self.port})")
    
    def send_frame(self, frame: np.ndarray, img_num: int = None) -> bool:
        """프레임 전송
        Args:
            frame: 전송할 프레임
            img_num: 이미지 번호 (None이면 번호 없이 전송)
        Returns:
            bool: 성공 여부
        """
        try:
            # 프레임 인코딩
            _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # 이미지 번호 추가
            if img_num is not None:
                data = f"{img_num}:".encode() + img_encoded.tobytes()
            else:
                data = img_encoded.tobytes()
            
            # 전송
            self.socket.sendto(data, (self.host, self.port))
            return True
            
        except Exception as e:
            if self.running:
                print(f"[ERROR] 프레임 전송 오류: {e}")
            return False 