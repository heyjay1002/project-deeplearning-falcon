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

        # === ArUco 월드 좌표 (mm 단위) ===
        # 기준 마커 4개의 실제 세계 좌표 (좌상단부터 시계방향)
        self.ARUCO_WORLD_CORNERS = [
            (435.0, 390.0),   # ID 0: (43.5, -39)cm -> (435, 390)mm
            (1375.0, 390.0),  # ID 1: (137.5, -39)cm -> (1375, 390)mm
            (1375.0, 1290.0), # ID 2: (137.5, -129)cm -> (1375, 1290)mm
            (435.0, 1290.0)   # ID 3: (43.5, -129)cm -> (435, 1290)mm
        ]

        # === 전체 맵 구역의 실제 세계 좌표 (mm 단위) [디버깅용] ===
        # 맵의 원점 (0,0)을 기준으로 각 구역의 모서리 좌표를 정의
        self.WORLD_ZONES = {
            # RWY 구역: 맵 가로 전체를 포함하는 수평 스트립
            "RWY_A":   [(0, 0),    (1800, 0),   (1800, 300),  (0, 300)],
            "RWY_B":   [(0, 650),  (1800, 650), (1800, 950),  (0, 950)],

            # TWY 및 GRASS 구역: 각자의 사각형 칸
            "TWY_A":   [(0, 300),   (350, 300),  (350, 650),  (0, 650)],
            "GRASS_A": [(350, 300), (1450, 300), (1450, 650), (350, 650)],
            "TWY_B":   [(1450, 300),(1800, 300), (1800, 650), (1450, 650)],
            
            "TWY_C":   [(0, 950),   (350, 950),  (350, 1350), (0, 1350)],
            "GRASS_B": [(350, 950), (1450, 950), (1450, 1350), (350, 1350)],
            "TWY_D":   [(1450, 950),(1800, 950), (1800, 1350), (1450, 1350)],
        }
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
        self.MAIN_SERVER_IP = "192.168.0.12"
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
        self.DEBUG_SHOW_ZONES = True  #  원본 영상에 구역을 반투명하게 표시

settings = Settings() 