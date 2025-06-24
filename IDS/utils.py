# utils.py

import time
import logging

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
    '''
    목적: 두 개의 바운딩 박스 간 IoU(Intersection over Union) 계산
    boxA, boxB는 [x1, y1, x2, y2] 형식
    두 박스의 겹치는 영역(interArea) 넓이 계산
    각각의 박스 넓이(boxAArea, boxBArea) 계산
    IoU = inter / (A + B - inter) 공식 적용
    사용 위치:  detector.py에서 ArUco 마커와 감지된 객체가 겹치는지 필터링할 때 사용
    '''
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

def estimate_pose_status(pose_result):
    '''
    목적: YOLO pose 모델의 keypoints를 바탕으로 사람이 서 있는지/넘어진 상태인지 판정
    keypoints의 y 좌표값만 추출
    최대값과 최소값 차이(y_vals.max() - y_vals.min())를 기준으로
    40px 미만이면 넘어진 것(FALLEN) 으로 판단
    그렇지 않으면 서 있음(STAND)
    '''
    try:
        keypoints = pose_result.keypoints[0].xy.cpu().numpy()
        y_vals = keypoints[:, 1]
        if (y_vals.max() - y_vals.min()) < 40:
            return "FALLEN"
        else:
            return "STAND"
    except:
        return "STAND"
# 고유 id 생성
def generate_our_id(tracker_id):
    return int(str(int(time.time() * 1000)) + str(tracker_id))