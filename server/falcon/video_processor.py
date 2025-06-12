"""
비디오 프로세서 모듈
- 비디오 프레임 처리
- 프레임 버퍼 관리
- FPS 계산
"""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
import time
from collections import deque

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

class VideoProcessor(QThread):
    """비디오 프레임 처리를 담당하는 클래스"""
    # 시그널 정의
    frame_processed = pyqtSignal(dict)  # 처리된 프레임 전달용 시그널
    buffer_status_ready = pyqtSignal(str)  # 버퍼 상태 전달용 시그널
    stats_ready = pyqtSignal(dict)  # 통계 전달용 시그널
    
    def __init__(self):
        super().__init__()
        # 프레임 버퍼 초기화
        self.frame_buffer = {}
        self.frame_queue = deque(maxlen=VIDEO_FRAME_BUFFER)
        self.buffer_ready = False
        self.displayed_img_id = None
        
        # FPS 계산기
        self.fps_calc = FPSCalculator()
        
        # 마지막 처리 결과 저장
        self.last_processed_frame = None
        self.last_processed_img_id = None
    
    def process_frame(self, frame_data):
        """프레임 처리
        Args:
            frame_data (dict): {
                'frame': np.ndarray,  # 처리할 프레임
                'img_id': int,  # 이미지 ID
                'cam_id': str  # 카메라 ID
            }
        """
        if not frame_data or 'frame' not in frame_data:
            return
        
        frame = frame_data['frame']
        img_id = frame_data['img_id']
        
        # 프레임 버퍼에 저장
        self.frame_buffer[img_id] = frame.copy()
        self.frame_queue.append(img_id)
        
        # 버퍼 상태 업데이트
        buffer_status = f"버퍼: {len(self.frame_queue)}/{VIDEO_FRAME_BUFFER} 프레임"
        if not self.buffer_ready:
            buffer_status += " (준비 중...)"
        self.buffer_status_ready.emit(buffer_status)
        
        # 버퍼 준비 확인
        if not self.buffer_ready and len(self.frame_queue) >= VIDEO_FRAME_BUFFER:
            self.buffer_ready = True
            self.displayed_img_id = self.frame_queue[0]
            print(f"[INFO] 버퍼 준비 완료")
        
        # 프레임 처리 및 전송
        if self.buffer_ready and self.displayed_img_id in self.frame_buffer:
            current_frame = self.frame_buffer[self.displayed_img_id]
            
            # 처리된 프레임 전달
            processed_data = {
                'frame': current_frame.copy(),
                'img_id': self.displayed_img_id
            }
            self.frame_processed.emit(processed_data)
            
            # FPS 계산 및 통계 업데이트
            if self.fps_calc.update():
                stats = {
                    'fps': round(self.fps_calc.current_fps, 1),
                    'img_id': self.displayed_img_id
                }
                self.stats_ready.emit(stats)
            
            # 다음 프레임으로 이동
            if len(self.frame_queue) > 0:
                current_idx = self.frame_queue.index(self.displayed_img_id)
                if current_idx + 1 < len(self.frame_queue):
                    self.displayed_img_id = self.frame_queue[current_idx + 1]
            
            # 오래된 프레임 제거
            while len(self.frame_buffer) > VIDEO_FRAME_BUFFER and len(self.frame_queue) > 0:
                oldest_id = self.frame_queue[0]
                if oldest_id == self.displayed_img_id:
                    break
                self.frame_buffer.pop(oldest_id, None)
                self.frame_queue.remove(oldest_id)
    
    def get_frame(self, img_id):
        """특정 이미지 ID의 프레임 반환"""
        return self.frame_buffer.get(img_id)
    
    def clear_buffer(self):
        """버퍼 초기화"""
        self.frame_buffer.clear()
        self.frame_queue.clear()
        self.buffer_ready = False
        self.displayed_img_id = None 