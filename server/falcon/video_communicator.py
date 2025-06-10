"""
비디오 통신을 담당하는 VideoCommunicator 클래스
- UDP를 통한 영상 수신/전송
- 프레임 버퍼 관리
- 서버 GUI 및 Admin GUI와의 통신
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
    # 서버 GUI 업데이트용 시그널
    server_frame_ready = pyqtSignal(dict)  # 서버 GUI에 프레임 표시
    server_stats_ready = pyqtSignal(dict)  # 서버 GUI 통계 업데이트
    server_buffer_status_ready = pyqtSignal(str)  # 서버 GUI 버퍼 상태 표시
    
    def __init__(self, video_processor):
        super().__init__()
        # IDS 비디오 수신기 초기화 (IDS -> 서버)
        self.video_receiver = UDPVideoReceiver(port=UDP_PORT_IDS_VIDEO)
        
        # Admin GUI 비디오 전송기 초기화 (서버 -> Admin)
        self.admin_video_sender = UDPVideoSender(host=DEFAULT_CLIENT_HOST, port=UDP_PORT_ADMIN_VIDEO)
        
        # 프레임 버퍼 (2초 분량)
        self.frame_buffer = {}
        self.frame_queue = deque(maxlen=VIDEO_FRAME_BUFFER)
        self.buffer_ready = False
        self.displayed_seq = None
        
        # FPS 계산기
        self.fps_calc = FPSCalculator()
        
        # 비디오 프로세서 연결
        self.video_processor = video_processor
        self.video_processor.frame_processed.connect(self._on_detection_ready)
        
        # 마지막 검출 결과 저장
        self.last_detection = None
        self.last_detection_seq = None
    
    def run(self):
        """메인 실행 루프"""
        # IDS로부터 영상 수신 시작
        self.video_receiver.start()
        # Admin GUI로 영상 전송 시작
        self.admin_video_sender.start()
        
        total_frames = 0
        
        while self.video_receiver.running:
            # IDS로부터 프레임 수신
            frame, seq_num = self.video_receiver.receive_frame()
            if frame is None:
                time.sleep(0.001)  # CPU 사용량 감소
                continue
            
            # 프레임 처리
            self._process_frame(frame, seq_num, total_frames)
            total_frames += 1
    
    def _process_frame(self, frame, seq_num, total_frames):
        """프레임 처리"""
        # 프레임 저장
        self.frame_buffer[seq_num] = frame.copy()
        self.frame_queue.append(seq_num)
        
        # 버퍼 상태 업데이트
        buffer_status = f"버퍼: {len(self.frame_queue)}/{VIDEO_FRAME_BUFFER} 프레임"
        if not self.buffer_ready:
            buffer_status += " (준비 중...)"
        self.server_buffer_status_ready.emit(buffer_status)
        
        # 버퍼 준비 확인
        if not self.buffer_ready and len(self.frame_queue) >= VIDEO_FRAME_BUFFER:
            self.buffer_ready = True
            self.displayed_seq = min(self.frame_buffer.keys())
            print(f"[INFO] 버퍼 준비 완료")
        
        # 프레임 처리 및 전송
        if self.buffer_ready and self.displayed_seq in self.frame_buffer:
            current_frame = self.frame_buffer[self.displayed_seq]
            
            # YOLO 처리를 위해 프레임 전달 (비동기)
            if self.displayed_seq % 3 == 0:  # 3프레임마다 YOLO 처리 요청
                self.video_processor.process_frame({
                    'frame': current_frame.copy(),
                    'seq': self.displayed_seq
                })
            
            # 현재 프레임에 검출 결과 적용
            frame_with_boxes = current_frame.copy()
            if self.last_detection is not None:
                # 이전 검출 결과와 현재 프레임의 시퀀스 번호 차이가 너무 크지 않은 경우에만 사용
                seq_diff = self.displayed_seq - self.last_detection_seq
                if 0 <= seq_diff <= 5:  # 최대 5프레임까지만 이전 결과 사용
                    frame_with_boxes = self._draw_detections(frame_with_boxes, self.last_detection)
            
            # GUI로 프레임 전송
            self.admin_video_sender.send_frame(frame_with_boxes)
            
            frame_data = {
                'frame': frame_with_boxes,
                'seq': self.displayed_seq
            }
            self.server_frame_ready.emit(frame_data)
            
            # FPS 계산 및 통계 업데이트
            if self.fps_calc.update():
                stats = {
                    'fps': round(self.fps_calc.current_fps, 1),
                    'seq': self.displayed_seq,
                    'total_frames': total_frames
                }
                self.server_stats_ready.emit(stats)
            
            # 다음 프레임으로 이동
            next_seq = self.displayed_seq + 1
            if next_seq in self.frame_buffer:
                self.displayed_seq = next_seq
            
            # 오래된 프레임 제거
            while len(self.frame_buffer) > VIDEO_FRAME_BUFFER:
                oldest_seq = min(self.frame_buffer.keys())
                if oldest_seq >= self.displayed_seq:
                    break
                self.frame_buffer.pop(oldest_seq, None)
    
    def _draw_detections(self, frame, detections):
        """검출 결과를 프레임에 그리기"""
        frame_with_boxes = frame.copy()
        for detection in detections:
            bbox = detection.get('bbox', [])
            if not bbox or len(bbox) != 4:
                continue
            
            x1, y1, x2, y2 = map(int, bbox)
            cls = detection.get('class', 'Unknown')
            conf = detection.get('confidence', 0.0)
            
            # 박스 그리기
            cv2.rectangle(frame_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 레이블 표시
            label = f"{cls}: {conf:.2f}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame_with_boxes, (x1, y1 - label_h - 10), (x1 + label_w, y1), (0, 255, 0), -1)
            cv2.putText(frame_with_boxes, label, (x1, y1 - 5),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return frame_with_boxes
    
    def _on_detection_ready(self, processed_data):
        """VideoProcessor에서 새로운 검출 결과 수신"""
        if processed_data.get('detections'):
            self.last_detection = processed_data['detections']
            self.last_detection_seq = processed_data['seq']
    
    def stop(self):
        """통신 중지"""
        self.video_receiver.close()  # IDS 수신 중지
        self.admin_video_sender.close()  # Admin GUI 전송 중지 