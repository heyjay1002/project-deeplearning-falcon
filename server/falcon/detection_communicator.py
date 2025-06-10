"""
감지 결과 통신을 담당하는 DetectionCommunicator 클래스
IDS로부터 객체 검출 이벤트를 수신하고 처리
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time

from network.tcp import TCPServer
from config import *

class FPSCalculator:
    """FPS 계산을 위한 유틸리티 클래스"""
    def __init__(self):
        self.frame_count = 0
        self.last_time = time.time()
        self.current_fps = 0
        self.processing_time = 0  # 처리 시간 (ms)
    
    def update(self, processing_time_ms=0):
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        # 메시지 수신 시점 기준으로 FPS 계산
        self.frame_count += 1
        self.processing_time = processing_time_ms
        
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_time = current_time
            return True
        return False

class DetectionCommunicator(QThread):
    """감지 결과 통신을 담당하는 클래스"""
    # 시그널 정의
    stats_ready = pyqtSignal(dict)
    
    def __init__(self, detection_buffer):
        """
        Args:
            detection_buffer (dict): 비디오 스레드와 공유하는 감지 결과 버퍼
        """
        super().__init__()
        # TCP 서버 초기화 (IDS로부터 감지 결과 수신용)
        self.detection_server = TCPServer(port=TCP_PORT_IMAGE)
        
        # 감지 결과 버퍼 (비디오 스레드와 공유)
        self.detection_buffer = detection_buffer
        
        # 수신 카운터
        self.receive_count = 0
        
        # FPS 계산기
        self.fps_calc = FPSCalculator()
    
    def run(self):
        """메인 실행 루프"""
        self.detection_server.start()
        
        print("[INFO] 감지 결과 통신 시작")
        
        while self.detection_server.running:
            # 새로운 클라이언트 연결 수락
            self.detection_server.accept_client()
            
            # 데이터 수신 시작 시간
            start_time = time.time()
            
            # 데이터 수신
            messages = self.detection_server.receive_data()
            if messages:  # 데이터가 있을 때만 처리
                # 수신 카운터 증가 및 출력
                self.receive_count += 1
                print(f"[INFO] 메시지 수신 #{self.receive_count}")
                
                # 메시지 처리
                self._process_messages(messages)
                
                # 처리 시간 계산 (밀리초)
                processing_time = (time.time() - start_time) * 1000
                
                # FPS 및 통계 업데이트
                if self.fps_calc.update(processing_time):
                    stats = {
                        'fps': round(self.fps_calc.current_fps, 1),
                        'processing_time': round(self.fps_calc.processing_time, 1)
                    }
                    self.stats_ready.emit(stats)
            
            time.sleep(0.001)  # CPU 사용량 감소
    
    def _process_messages(self, messages):
        """메시지 처리
        
        Args:
            messages (list): 수신된 메시지 리스트
        """
        for message in messages:
            # 메시지 타입 확인
            if message.get('type') != 'event' or message.get('event') != 'object_detected':
                print(f"[WARNING] 알 수 없는 메시지: {message.get('type')}, {message.get('event')}")
                continue
            
            # 감지 결과 처리
            camera_id = message.get('camera_id', 'Unknown')
            detections = message.get('detections', [])
            for detection in detections:
                img_id = detection.get('img_id')
                if img_id is None:
                    print("[WARNING] 이미지 ID 없음")
                    continue
                
                # 버퍼에 저장 (카메라 ID 포함)
                if img_id not in self.detection_buffer:
                    self.detection_buffer[img_id] = []
                detection['camera_id'] = camera_id  # 카메라 ID 추가
                self.detection_buffer[img_id].append(detection)
    
    def stop(self):
        """통신 중지"""
        print("[INFO] 감지 결과 통신 중지")
        self.detection_server.close() 