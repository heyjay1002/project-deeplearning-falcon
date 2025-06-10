"""
비디오 프로세서 모듈
- YOLO 객체 검출 처리
- 검출 결과 전달
"""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from config import *

class VideoProcessor(QThread):
    """비디오 프레임 처리를 담당하는 클래스"""
    frame_processed = pyqtSignal(dict)  # 처리된 프레임 전달용 시그널
    
    def __init__(self, detection_buffer):
        super().__init__()
        # 검출 결과 버퍼 (TCP 스레드와 공유)
        self.detection_buffer = detection_buffer
    
    def process_frame(self, frame_data):
        """프레임 처리 요청
        Args:
            frame_data (dict): {
                'frame': np.ndarray,  # 처리할 프레임
                'seq': int  # 프레임 시퀀스 번호
            }
        """
        if not frame_data or 'frame' not in frame_data:
            return
        
        seq = frame_data['seq']
        
        # 현재 프레임의 검출 결과 가져오기
        detections = self.detection_buffer.get(seq, [])
        
        # 검출 결과 전달
        processed_data = {
            'detections': detections,
            'seq': seq
        }
        self.frame_processed.emit(processed_data)
    
    def stop(self):
        """처리 중지"""
        pass  # TCP 통신은 DetectionCommunicator에서 처리 