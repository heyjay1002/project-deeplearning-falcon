"""
검출 프로세서 모듈
- 객체 검출 결과 처리
- 검출 결과 시각화
- 검출 통계 관리
"""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
import time
from datetime import datetime
from db.repository import DetectionRepository
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os

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

class DetectionProcessor(QThread):
    """객체 검출 결과 처리를 담당하는 클래스"""
    # 시그널 정의
    detection_processed = pyqtSignal(dict)  # 처리된 검출 결과 전달용 시그널
    stats_ready = pyqtSignal(dict)  # 통계 전달용 시그널
    
    def __init__(self, video_processor=None):
        super().__init__()
        # 검출 결과 버퍼
        self.detection_buffer = {}
        
        # FPS 계산기
        self.fps_calc = FPSCalculator()
        
        # 마지막 처리 결과 저장
        self.last_detection = None
        self.last_detection_img_id = None
        
        # 경고 전송된 객체 ID 추적 (메모리 캐시)
        self.alerted_object_ids = set()
        
        # 데이터베이스 리포지토리 초기화
        self.repository = DetectionRepository(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        # VideoProcessor 참조 저장
        self.video_processor = video_processor
        
        # 실행 상태
        self.running = True
    
    def process_detection(self, detection_data):
        """검출 결과 처리
        Args:
            detection_data (dict): {
                'img_id': int,  # 이미지 ID
                'detections': list  # 검출 결과 리스트
            }
        """
        if not detection_data or 'detections' not in detection_data:
            return
        
        img_id = detection_data['img_id']
        detections = detection_data['detections']
        
        # 검출 결과 버퍼에 저장
        self.detection_buffer[img_id] = detections
        
        # 마지막 검출 결과 업데이트
        self.last_detection = detections
        self.last_detection_img_id = img_id
        
        # 처리된 검출 결과 전달
        processed_data = {
            'detections': detections,
            'img_id': img_id
        }
        self.detection_processed.emit(processed_data)
        
        # FPS 계산 및 통계 업데이트
        if self.fps_calc.update():
            stats = {
                'fps': round(self.fps_calc.current_fps, 1)
            }
            self.stats_ready.emit(stats)
        
        try:
            # 데이터베이스에 저장
            if detections:
                # 최초 경고된 객체들만 필터링 (alerted_object_ids에 없는 ID만)
                new_detections = []
                for detection in detections:
                    object_id = detection['object_id']
                    if object_id not in self.alerted_object_ids:
                        new_detections.append(detection)
                        self.alerted_object_ids.add(object_id)  # 경고 목록에 추가
                
                # 최초 경고된 객체들에 대해서만 이미지 생성 및 DB 저장
                if new_detections and self.video_processor:
                    frame = self.video_processor.get_frame(img_id)
                    if frame is not None:
                        saved_detections = []
                        crop_imgs = []
                        for detection in new_detections:
                            # 이미지 저장 후 실제 파일 경로 받기
                            saved_img_path = self.save_cropped_frame(frame, detection, img_id)
                            if saved_img_path:
                                # detection에 실제 저장된 파일 경로 추가
                                detection['img_path'] = saved_img_path
                                
                                bbox = detection.get('bbox', [])
                                if bbox and len(bbox) == 4:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    crop = frame[y1:y2, x1:x2]
                                    _, img_encoded = cv2.imencode('.jpg', crop)
                                    crop_imgs.append(img_encoded.tobytes())
                                    saved_detections.append(detection)
                        if saved_detections:
                            success = self.repository.save_detection_event(
                                camera_id='A',
                                img_id=img_id,
                                detections=saved_detections,
                                crop_imgs=crop_imgs
                            )
                            if success:
                                print(f"[INFO] ME_FD 저장 완료: {len(saved_detections)}개 객체")
            
        except Exception as e:
            print(f"[ERROR] 감지 결과 처리 중 오류: {e}")
    
    def draw_detections(self, frame, img_id):
        """검출 결과를 프레임에 시각화
        Args:
            frame (np.ndarray): 원본 프레임
            img_id (int): 이미지 ID
        Returns:
            np.ndarray: 검출 결과가 그려진 프레임
        """
        frame_with_boxes = frame.copy()
        
        # 주기적으로 오래된 검출 결과 정리 (매 50번째 호출마다)
        if hasattr(self, '_draw_count'):
            self._draw_count += 1
        else:
            self._draw_count = 1
            
        if self._draw_count % 50 == 0:
            self.cleanup_old_detections(img_id)
        
        # 현재 프레임의 검출 결과 확인
        if img_id in self.detection_buffer:
            detections = self.detection_buffer[img_id]
        else:
            # 현재 프레임보다 이전의 가장 가까운 검출 결과 찾기
            prev_frame_id = None
            for frame_id in self.detection_buffer.keys():
                if frame_id < img_id and (prev_frame_id is None or frame_id > prev_frame_id):
                    prev_frame_id = frame_id
            
            if prev_frame_id is not None:
                detections = self.detection_buffer[prev_frame_id]
            else:
                return frame_with_boxes
        
        # 검출 결과 시각화
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
    
    def get_detection(self, img_id):
        """특정 이미지 ID의 검출 결과 반환"""
        return self.detection_buffer.get(img_id)
    
    def clear_buffer(self):
        """버퍼 초기화"""
        self.detection_buffer.clear()
        self.last_detection = None
        self.last_detection_img_id = None
    
    def stop(self):
        """처리 중지"""
        self.running = False
        self.repository.close()

    def crop_frame(self, frame, detection):
        """bbox로 프레임을 crop하여 이미지로 저장
        Args:
            frame (np.ndarray): 원본 프레임
            detection (dict): 검출 결과
        Returns:
            np.ndarray: 저장된 이미지
        """
        bbox = detection.get('bbox', [])
        if not bbox or len(bbox) != 4:
            return None
        
        x1, y1, x2, y2 = map(int, bbox)
        cropped_frame = frame[y1:y2, x1:x2]
        return cropped_frame

    def save_cropped_frame(self, frame, detection, img_id):
        cropped_frame = self.crop_frame(frame, detection)
        if cropped_frame is None:
            print(f"[ERROR] Crop 실패: object_id={detection.get('object_id')}, bbox={detection.get('bbox')}")
            return None
        img_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'img')
        os.makedirs(img_dir, exist_ok=True)
        filename = f"img_{detection['object_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        filepath = os.path.join(img_dir, filename)
        result = cv2.imwrite(filepath, cropped_frame)
        if result:
            print(f"[INFO] 이미지 저장 완료: {filename}")
            return f"img/{filename}"  # DB에 저장할 상대 경로 반환
        else:
            print(f"[ERROR] 이미지 저장 실패: {filename}")
            return None

    def cleanup_old_detections(self, current_img_id, max_age_ns=1_000_000_000):
        """오래된 검출 결과 정리 (5초 이상 or 50개 이상)"""
        current_time = current_img_id
        old_keys = []
        
        for frame_id in self.detection_buffer.keys():
            if current_time - frame_id > max_age_ns:
                old_keys.append(frame_id)
        
        for key in old_keys:
            del self.detection_buffer[key]
        
        # if old_keys:
        #     print(f"[INFO] 버퍼 정리: {len(old_keys)}개 오래된 검출 결과 삭제됨 (버퍼 크기: {len(self.detection_buffer)})") 