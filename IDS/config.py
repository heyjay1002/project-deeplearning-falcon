# config.py
import os
import numpy as np

class Settings:
    def __init__(self):
        # === 클래스 정의 ===
        self.CLASS_NAMES = {
            0: "BIRD",
            1: "FOD",
            2: "PERSON",
            3: "ANIMAL",
            4: "AIRPLANE",
            5: "VEHICLE",
            6: "WORK_PERSON",
            7: "WORK_VEHICLE",
        }
        self.CLASS_NAME_TO_ID = {v: k for k, v in self.CLASS_NAMES.items()}

        # === YOLO 설정 ===
        self.DETECTING_MODEL_PATH = "models/yolov8n_box_v0.1.0.pt"
        self.MODEL_PATH_POSE = "models/pose_model_v1.pt"
        self.TRACKER_CONFIG_FILE = "bytetrack.yaml"  # 또는 "botsort.yaml"


        self.YOLO_CONFIDENCE_THRESHOLD = 0.6
        self.YOLO_IOU_THRESHOLD = 0.5

        # === 색상 분류 HSV 범위 ===
        self.VEST_HSV_LOWER = (10, 100, 150)
        self.VEST_HSV_UPPER = (25, 255, 255)
        self.VEHICLE_YELLOW_LOWER = (20, 100, 100)
        self.VEHICLE_YELLOW_UPPER = (30, 255, 255)
        self.VEHICLE_BLACK_LOWER = (0, 0, 0)
        self.VEHICLE_BLACK_UPPER = (180, 255, 50)

        # === ArUco 마커 ===
        self.MARKER_LENGTH = 0.18  # meter
        self.ARUCO_WORLD = [
            (0.00, 0.00),
            (2.00, 0.00),
            (2.00, 1.50),
            (0.00, 1.50)
        ]
        self.ENABLE_ARUCO_MASK_FILTER = True

        # === 카메라 설정 ===
        self.CAMERA_ID = "A"
        # ls /dev/video*
        self.CAMERA_PATH = 2
        self.CAMERA_USE_MJPG = True
        self.CAPTURE_RESOLUTION = (960, 960)
        self.PROCESS_RESOLUTION = (960, 960)
        self.CAMERA_FPS = 30
        self.JPEG_QUALITY = 30
        # === 네트워크 설정 ===
        self.MAIN_SERVER_IP = "192.168.0.2"
        self.IDS_UDP_PORT = 4000
        self.IDS_TCP_PORT = 5000
        self.TCP_COMM_TIMEOUT_MS = 5000

        # === 구조 감지 ===
        self.RESCUE_LEVEL_MAX = 10
        self.RESCUE_LEVEL_STEP_SEC = 1

        # === 큐 크기 ===
        self.INFERENCE_QUEUE_SIZE = 10
        self.TCP_EVENT_QUEUE_SIZE = 10

        # === 디버깅 ===
        self.DISPLAY_DEBUG = False
        self.LOG_LEVEL = "INFO"
        
settings = Settings() 