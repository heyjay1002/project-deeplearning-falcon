# utils.py

import time
import logging
import numpy as np
import math

class FPSMeter:
    def __init__(self):
        self.frame_count = 0
        self.last_time = time.time()
        self.current_fps = 0

    def update(self):
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_time
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_time = now
            return True
        return False

    def get(self):
        return self.current_fps

def setup_logger(name='IDS', level='INFO'):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

def bbox_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    if interArea == 0:
        return 0.0
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

# [수정] 쓰러짐 판단 기준으로 bbox 비율 함수만 남기고 나머지 제거
def estimate_by_bbox_ratio(bbox):
    """
    Bbox의 가로/세로 비율로 쓰러짐 상태를 판정합니다.
    - 너비가 높이보다 1.3배 이상 크면 'FALLEN'으로 간주합니다.
    """
    try:
        x1, y1, x2, y2 = bbox
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        
        # 높이가 0인 경우의 예외 처리
        if bbox_height == 0:
            return "FALLEN"
            
        aspect_ratio = bbox_width / bbox_height
        
        # 비율 임계값(1.3)은 실험을 통해 조정 가능
        return "FALLEN" if aspect_ratio > 1.3 else "STAND"
    except:
        # 오류 발생 시 기본값 'N/A' 반환
        return "N/A"

def generate_our_id(tracker_id):
    return int(str(int(time.time() * 1000)) + str(tracker_id))