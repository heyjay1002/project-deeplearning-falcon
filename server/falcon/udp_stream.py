"""
비디오 통신을 담당하는 VideoCommunicator 클래스
- UDP를 통한 영상 수신/전송
- 프레임 전달
"""

import cv2
import numpy as np
import time
from collections import deque
from PyQt6.QtCore import QThread, pyqtSignal

from network.udp import UDPVideoReceiver, UDPVideoSender
from config import *

class FPSCalculator:
    """FPS 계산을 위한 유틸리티 클래스"""
    def __init__(self):
        self.frame_count = 0
        self.last_time = time.time()
        self.current_fps = 0
    
    def update(self):
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_time = current_time
            return True
        return False

class VideoCommunicator(QThread):
    """비디오 통신을 담당하는 클래스"""
    # 시그널 정의
    frame_received = pyqtSignal(dict)  # 프레임 수신 시그널
    
    def __init__(self):
        super().__init__()
        # IDS 비디오 수신기 초기화 (IDS -> 서버)
        self.video_receiver = UDPVideoReceiver(port=UDP_PORT_IDS_VIDEO)
        
        # Admin GUI 비디오 전송기 초기화 (서버 -> Admin)
        self.admin_video_sender = UDPVideoSender(host=DEFAULT_CLIENT_HOST, port=UDP_PORT_ADMIN_VIDEO)
    
    def run(self):
        """메인 실행 루프"""
        # IDS로부터 영상 수신 시작
        self.video_receiver.start()
        # Admin GUI로 영상 전송 시작
        self.admin_video_sender.start()
        
        while self.video_receiver.running:
            # IDS로부터 프레임 수신
            frame, cam_id, img_id = self.video_receiver.receive_frame()
            if frame is None:
                time.sleep(0.001)  # CPU 사용량 감소
                continue
            
            # 프레임 전달
            frame_data = {
                'frame': frame,
                'img_id': img_id,
                'cam_id': cam_id
            }
            self.frame_received.emit(frame_data)
            
            # Admin GUI로 프레임 전송
            self.admin_video_sender.send_frame(frame)
    
    def stop(self):
        """통신 중지"""
        self.video_receiver.close()  # IDS 수신 중지
        self.admin_video_sender.close()  # Admin GUI 전송 중지 