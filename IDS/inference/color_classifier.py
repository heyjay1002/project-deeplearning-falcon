# inference/color_classifier.py

import cv2
import numpy as np
from config.config import settings

class ColorClassifier:
    """
    OpenCV를 사용하여 특정 색상 패턴을 감지하고 클래스를 세분화하는 클래스.
    'Person' -> 'Worker' (형광 조끼)
    'Car' -> 'Work Vehicle' (노란색/검은색 조합)
    """
    def __init__(self):
        # 형광 조끼 (주황색/노란색 계열) HSV 색상 범위 정의
        self.LOWER_VEST_ORANGE = np.array([10, 100, 150])
        self.UPPER_VEST_ORANGE = np.array([25, 255, 255])
        
        # 작업 차량 (노란색) HSV 색상 범위 정의
        self.LOWER_VEHICLE_YELLOW = np.array([20, 100, 100])
        self.UPPER_VEHICLE_YELLOW = np.array([30, 255, 255])

        # 작업 차량 (검정색) HSV 색상 범위 정의
        self.LOWER_VEHICLE_BLACK = np.array([0, 0, 0])
        self.UPPER_VEHICLE_BLACK = np.array([180, 255, 50])

    def is_worker(self, frame: np.ndarray, person_bbox: list) -> bool:
        x1, y1, x2, y2 = map(int, person_bbox)
        upper_body_y_end = y1 + int((y2 - y1) * 0.6)
        person_upper_body = frame[y1:upper_body_y_end, x1:x2]
        if person_upper_body.size == 0: return False
        
        hsv_upper_body = cv2.cvtColor(person_upper_body, cv2.COLOR_BGR2HSV)
        vest_mask = cv2.inRange(hsv_upper_body, self.LOWER_VEST_ORANGE, self.UPPER_VEST_ORANGE)
        vest_ratio = np.sum(vest_mask > 0) / (person_upper_body.size / 3)
        
        return vest_ratio > 0.05

    def is_work_vehicle(self, frame: np.ndarray, car_bbox: list) -> bool:
        x1, y1, x2, y2 = map(int, car_bbox)
        car_roi = frame[y1:y2, x1:x2]
        if car_roi.size == 0: return False
        
        hsv_car = cv2.cvtColor(car_roi, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(hsv_car, self.LOWER_VEHICLE_YELLOW, self.UPPER_VEHICLE_YELLOW)
        black_mask = cv2.inRange(hsv_car, self.LOWER_VEHICLE_BLACK, self.UPPER_VEHICLE_BLACK)
        
        yellow_ratio = np.sum(yellow_mask > 0) / (car_roi.size / 3)
        black_ratio = np.sum(black_mask > 0) / (car_roi.size / 3)
        
        return yellow_ratio > 0.1 and black_ratio > 0.1