# inference/detector.py

import torch
from ultralytics import YOLO 
import numpy as np
import cv2 
from config.config import settings
from .color_classifier import ColorClassifier

class Detector:
    """
    딥러닝 모델(YOLO)을 로드하고, 입력 프레임에 대해 객체 감지, 추적, 
    포즈 추정 및 색상 기반 재분류까지 모두 수행하는 클래스입니다.
    """
    def __init__(self, model_settings): 
        self.settings = model_settings
        self.detecting_model = None
        self.pose_model = None
        
        try:
            self.detecting_model = YOLO(self.settings.YOLO_DETECTING_MODEL_PATH)
            self.detecting_model.to('cuda')
            print(f"[Detector] YOLO Detecting model loaded: {self.settings.YOLO_DETECTING_MODEL_PATH}")
        except Exception as e:
            print(f"Error loading YOLO Detecting model: {e}")

        try:
            self.pose_model = YOLO(self.settings.YOLO_POSE_MODEL_PATH)
            self.pose_model.to('cuda')
            print(f"[Detector] YOLO-Pose model loaded: {self.settings.YOLO_POSE_MODEL_PATH}")
        except Exception as e:
            print(f"Error loading YOLO-Pose model: {e}")

        self.color_classifier = ColorClassifier()
        print("[Detector] ColorClassifier initialized.")

    def track(self, frame: np.ndarray, mode: str = "object_detect") -> dict:
        results = {'detections': [], 'tracked_objects': [], 'poses': [], 'markers': []}
        if mode != "object_detect" or not self.detecting_model:
            return results

        processed_frame = frame.copy()
        gray_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        processed_frame = cv2.cvtColor(clahe.apply(gray_frame), cv2.COLOR_GRAY2BGR) 
        
        # 1. 객체 탐지 및 추적, 재분류
        try:
            track_results = self.detecting_model.track(processed_frame, persist=True, conf=0.15, iou=0.7, verbose=False)
            if track_results and track_results[0].boxes.id is not None:
                boxes = track_results[0].boxes.xyxy.cpu().numpy()
                track_ids = track_results[0].boxes.id.cpu().numpy()
                classes = track_results[0].boxes.cls.cpu().numpy()
                confidences = track_results[0].boxes.conf.cpu().numpy()

                for i in range(len(boxes)):
                    bbox = boxes[i]
                    class_id = int(classes[i])
                    final_class_id = class_id

                    if class_id == self.settings.CLASS_ID_PERSON:
                        if self.color_classifier.is_worker(frame, bbox):
                            final_class_id = self.settings.CLASS_ID_WORKER
                    elif class_id == self.settings.CLASS_ID_CAR:
                        if self.color_classifier.is_work_vehicle(frame, bbox):
                            final_class_id = self.settings.CLASS_ID_WORK_VEHICLE

                    results['tracked_objects'].append({
                        'bbox': bbox.tolist(),
                        'object_id': int(track_ids[i]),
                        'class': self.settings.CLASS_NAMES[final_class_id],
                        'confidence': float(confidences[i]),
                        'pose': 'N/A'  # 포즈 정보 기본값으로 초기화
                    })
        except Exception as e:
            print(f"[Detector] Error during tracking/classification: {e}")

        # 2. 포즈 추정
        person_objects = [obj for obj in results['tracked_objects'] if obj['class'] in ['Person', 'Worker']]
        if self.pose_model and person_objects:
            try:
                pose_results = self.pose_model.predict(processed_frame, conf=0.5, verbose=False)
                for r in pose_results:
                    if r.keypoints and hasattr(r.keypoints, 'xy') and r.keypoints.xy.numel() > 0:
                        keypoints_xy_list = r.keypoints.xy.cpu().numpy().tolist()
                        boxes_pose_list = r.boxes.xyxy.cpu().numpy().tolist()
                        for i in range(len(keypoints_xy_list)):
                            results['poses'].append({
                                'keypoints': keypoints_xy_list[i], 
                                'bbox': boxes_pose_list[i] 
                            })
            except Exception as e:
                print(f"[Detector] Error during pose prediction: {e}")

        # --- 3. (핵심) Pose 정보와 추적된 객체 정보 결합 ---
        # tracked_objects의 각 Person/Worker에 해당하는 pose 정보를 찾아 삽입합니다.
        for person_obj in person_objects:
            px1, py1, px2, py2 = person_obj['bbox']
            
            for pose in results['poses']:
                kx1, ky1, kx2, ky2 = pose['bbox']
                # 포즈의 중심점이 사람의 바운딩 박스 안에 있는지 확인하여 매칭
                pose_center_x = (kx1 + kx2) / 2
                if px1 < pose_center_x < px2:
                    person_obj['pose'] = pose['keypoints'] # 실제 키포인트 데이터로 덮어쓰기
                    break # 가장 먼저 매칭된 포즈를 할당하고 루프 종료

        return results