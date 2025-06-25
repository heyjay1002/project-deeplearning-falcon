"""
UDP 통신을 위한 기본 클래스들
"""

import socket
import cv2
import numpy as np
from typing import Optional
from abc import ABC

from config import DEFAULT_HOST, DEFAULT_CLIENT_HOST, UDP_BUFFER_SIZE

class UDPBase(ABC):
    """UDP 통신을 위한 기본 클래스."""
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False

    def _init_socket(self) -> None:
        """UDP 소켓을 재사용 및 논블로킹 옵션과 함께 초기화."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, UDP_BUFFER_SIZE)
            self.socket.setblocking(False)
        except Exception as e:
            print(f"[오류] UDP 소켓 초기화 실패: {e}")
            raise

    def close(self) -> None:
        """UDP 소켓 종료."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"[경고] UDP 소켓 종료 중 오류 발생: {e}")
        self.socket = None

class UDPVideoReceiver(UDPBase):
    """UDP를 통해 비디오 프레임을 수신하는 수신자 클래스."""
    def __init__(self, host: str = DEFAULT_HOST, port: int = 0, with_img_id: bool = True):
        super().__init__(host, port)
        self.last_img_id = -1
        self.with_img_id = with_img_id

    def start(self) -> None:
        """소켓을 바인딩하고 수신 시작."""
        self._init_socket()
        self.socket.bind((self.host, self.port))
        self.running = True
        print(f"[UDP:{self.port}] 비디오 수신자 시작")

    def receive_frame(self):
        """비디오 프레임을 수신하고 디코딩. (프레임, 카메라ID, 이미지ID) 또는 (프레임, 카메라ID) 반환."""
        try:
            data, _ = self.socket.recvfrom(UDP_BUFFER_SIZE)
        except BlockingIOError:
            return (None, None, None) if self.with_img_id else (None, None)
        except Exception as e:
            if self.running:
                print(f"[오류] 프레임 수신 오류: {e}")
            return (None, None, None) if self.with_img_id else (None, None)

        # 카메라 ID 파싱
        sep = data.find(b':')
        if sep == -1:
            return (None, None, None) if self.with_img_id else (None, None)

        try:
            cam_id = data[:sep].decode()
        except Exception:
            return (None, None, None) if self.with_img_id else (None, None)

        # 이미지 ID 파싱 (포함된 경우)
        if self.with_img_id:
            sep2 = data.find(b':', sep + 1)
            if sep2 == -1:
                return None, None, None
            try:
                img_id = int(data[sep+1:sep2])
                if img_id <= self.last_img_id:
                    return None, None, None
                self.last_img_id = img_id
                frame_data = data[sep2+1:]
            except ValueError:
                return None, None, None
        else:
            frame_data = data[sep+1:]
            img_id = None

        frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return (None, None, None) if self.with_img_id else (None, None)

        return (frame, cam_id, img_id) if self.with_img_id else (frame, cam_id)

class UDPVideoSender(UDPBase):
    """UDP를 통해 비디오 프레임을 전송하는 송신자 클래스."""
    def __init__(self, host: str = DEFAULT_CLIENT_HOST, port: int = 0):
        super().__init__(host, port)

    def start(self) -> None:
        """소켓을 초기화하고 전송 활성화."""
        self._init_socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, UDP_BUFFER_SIZE)
        self.running = True
        print(f"[UDP:{self.port}] 비디오 송신자 시작 (대상: {self.host})")

    def send_frame(self, frame: np.ndarray, cam_id: str = "A", img_id: Optional[int] = None) -> bool:
        """비디오 프레임을 인코딩하고 전송 (선택적 이미지 ID 포함)."""
        try:
            # UDP 전송용 리사이즈 (960x960 -> 640x640)
            resized_frame = cv2.resize(frame, (960, 960))
            
            _, encoded = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
            header = f"{cam_id}:{img_id}:".encode() if img_id is not None else f"{cam_id}:".encode()
            final_data = header + encoded.tobytes()
            print(f"[DEBUG] UDP 전송 시도: 크기={len(final_data)}, 대상={self.host}:{self.port}")
            self.socket.sendto(final_data, (self.host, self.port))
            print(f"[DEBUG] UDP 전송 성공")
            return True
        except Exception as e:
            if self.running:
                print(f"[오류] 프레임 전송 오류: {e}")
            return False
