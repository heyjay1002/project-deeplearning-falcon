import cv2
import numpy as np
import torch
import threading
import time
import sys
import os
from ultralytics import YOLO

# Add root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from network import UDPVideoSender, TCPClient
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

class YOLOClient:
    def __init__(self, video_source=2, cam_id: str = "A"):
        self.running = True
        self.cam_id = cam_id  # 카메라 ID 추가
        
        # FPS 계산기
        self.video_fps_calc = FPSCalculator()
        self.detection_fps_calc = FPSCalculator()
        
        # 카메라 초기화
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            print("[ERROR] 카메라를 열 수 없습니다")
            self.running = False
            return
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, DEFAULT_FPS)
        
        # 최신 프레임 저장
        self.latest_frame = None
        self.latest_frame_img_id = None
        self.latest_frame_lock = threading.Lock()
        
        # YOLO 모델 로드
        self.model = YOLO('best2.pt')
        
        # 네트워크 클라이언트
        self.video_sender = UDPVideoSender(host=DEFAULT_HOST, port=UDP_PORT_IDS_VIDEO)
        self.detection_client = TCPClient(host=DEFAULT_HOST, port=TCP_PORT_IMAGE)
        
        # 시퀀스 번호
        self.img_id = 0
    
    def capture_and_send(self):
        """프레임 캡처 및 전송 스레드"""
        print(f"[INFO] 비디오 스트리밍 시작... (카메라 ID: {self.cam_id})")
        
        while self.running:
            try:
                start_time = time.time()
                
                ret, frame = self.cap.read()
                if not ret:
                    print(f"[ERROR] 프레임 읽기 실패 (카메라: {self.cam_id})")
                    continue
                
                # 나노초 단위의 타임스탬프로 img_id 생성
                img_id = time.time_ns()
                
                # 최신 프레임 업데이트
                with self.latest_frame_lock:
                    self.latest_frame = frame.copy()
                    self.latest_frame_img_id = img_id
                
                # 프레임 전송 (cam_id 포함)
                if not self.video_sender.send_frame(frame, cam_id=self.cam_id, img_id=img_id):
                    print(f"[WARNING] 프레임 전송 실패 (카메라: {self.cam_id}, img_id: {img_id})")
                
                # FPS 계산 및 출력
                if self.video_fps_calc.update():
                    print(f"[INFO] 현재 비디오 FPS: {self.video_fps_calc.current_fps:.1f} (카메라: {self.cam_id})")
                
                # FPS 조절
                elapsed = time.time() - start_time
                if elapsed < 1/DEFAULT_FPS:
                    time.sleep(1/DEFAULT_FPS - elapsed)
            
            except Exception as e:
                print(f"[ERROR] 프레임 캡처 중 오류 (카메라: {self.cam_id}): {e}")
                time.sleep(0.1)
    
    def detect_objects(self):
        """객체 감지 및 결과 전송 스레드"""
        print("[INFO] 객체 감지 시작...")
        last_processed_img_id = None  # 마지막으로 처리한 프레임 ID 저장
        
        while self.running:
            try:
                # 최신 프레임 가져오기
                with self.latest_frame_lock:
                    if self.latest_frame is None or self.latest_frame_img_id is None:
                        time.sleep(0.001)
                        continue
                    frame = self.latest_frame.copy()
                    img_id = self.latest_frame_img_id
                
                # 프레임이 바뀌었을 때만 감지
                if img_id == last_processed_img_id:
                    time.sleep(0.001)
                    continue
                last_processed_img_id = img_id
                
                # YOLO 객체 감지
                results = self.model(frame, conf=0.6, imgsz=640) #1920
                
                # 결과 처리
                detections = []
                for r in results:
                    boxes = r.boxes
                    for i, box in enumerate(boxes):
                        # xyxy 좌표, 신뢰도, 클래스
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = box.conf.item()
                        cls = box.cls.item()
                        
                        detections.append({
                            'object_id': 1000 + i,  # 각 객체마다 고유한 ID 부여
                            'class': self.model.names[int(cls)],  # 클래스 이름으로 변환
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': float(conf)
                        })
                
                # 검출이 있을 때만 전송
                if detections:
                    detection_data = {
                        'type': 'event',
                        'event': 'object_detected',
                        'camera_id': self.cam_id,
                        'img_id': img_id,
                        'detections': detections
                    }
                    
                    if not self.detection_client.send_message_json(detection_data):
                        print(f"[WARNING] 검출 결과 전송 실패 (img_id: {img_id})")
                    else:
                        print(f"[INFO] 검출 결과 전송 완료 (img_id: {img_id}, 객체 수: {len(detections)})")
                else:
                    # 검출이 없을 때는 로그만 출력 (선택적)
                    # print(f"[INFO] 검출 없음 (img_id: {img_id})")
                    pass
            
            except Exception as e:
                print(f"[ERROR] 객체 감지 중 오류: {e}")
                time.sleep(0.1)
    
    def start(self):
        """클라이언트 시작"""
        if not self.running:
            return False
        
        # 네트워크 연결
        self.video_sender.start()
        if not self.detection_client.start():
            print("[ERROR] 서버 연결 실패")
            return False
        
        # 서버로부터 'set_mode_object' 명령을 받을 때까지 대기
        print("[INFO] 'set_mode_object' 명령 대기 중...")
        while self.running:
            try:
                message = self.detection_client.receive_json()
                if message:
                    print(f"[RECV] {message}")
                    if message.get('type') == 'command' and message.get('command') == 'set_mode_object':
                        print("[INFO] 'set_mode_object' 명령 수신. 감지 및 전송을 시작합니다.")
                        break
                time.sleep(0.1)
            except Exception as e:
                print(f"[ERROR] 명령 수신 중 오류: {e}")
                self.stop()
                return False

        try:
            # 스레드 시작
            self.capture_thread = threading.Thread(target=self.capture_and_send)
            self.detect_thread = threading.Thread(target=self.detect_objects)
            
            self.capture_thread.start()
            self.detect_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 스레드 시작 실패: {e}")
            return False
    
    def stop(self):
        """클라이언트 종료"""
        print("[INFO] 클라이언트 종료 중...")
        self.running = False
        
        # 스레드 종료 대기
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join()
        if hasattr(self, 'detect_thread'):
            self.detect_thread.join()
        
        # 리소스 정리
        self.video_sender.close()
        self.detection_client.close()
        self.cap.release()
        
        print("[INFO] 클라이언트 종료 완료")

if __name__ == '__main__':
    client = YOLOClient(0)  # 기본 카메라 사용
    if client.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] 프로그램 종료 중...")
        finally:
            client.stop() 