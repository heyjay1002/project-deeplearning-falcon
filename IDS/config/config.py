'''
이 파일 하나에서 카메라 설정, 딥러닝 모델 경로, 네트워크 주소, 시각화 활성화 여부 등
시스템에 필요한 모든 설정값을 파이썬 변수로 정의하고 관리
'''

import os

class Settings:
    def __init__(self):
        # -----------------------------------------------------------
        # 1. 카메라 설정 (Camera Settings)
        # -----------------------------------------------------------
        # 실행 전 `ls -l /dev/video*`로 현재 할당된 이름을 확인하고 업데이트
        self.CAMERA_DEVICES = {
            "/dev/video2" : "CAM_A", # 첫 번째 웹캠의 장치 경로 
            "/dev/video4" : "CAM_B"# 두 번째 웹캠의 장치 경로 
        }
        
        self.CAMERA_RESOLUTION_WIDTH = 1920     # 카메라 캡처 해상도 (너비)
        self.CAMERA_RESOLUTION_HEIGHT = 1080    # 카메라 캡처 해상도 (높이)
        self.CAMERA_FPS = 30                    # 카메라 캡처 프레임 속도 (FPS)
        self.CAMERA_QUEUE_MAX_SIZE = 5          # multiprocessing.Queue의 최대 크기. 너무 커지면 지연 증가, 너무 작으면 프레임 드롭 가능성
        self.CAMERA_DROP_OLDEST_ON_FULL = True       

        # -----------------------------------------------------------
        # 2. 모델 설정 (Model Settings)

        # `config.py` 파일이 있는 디렉토리를 기준으로 `models` 폴더의 경로를 설정
        self.MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
        
        # YOLO Detecting 모델 파일 경로
        self.YOLO_DETECTING_MODEL_PATH = os.path.join(self.MODELS_DIR, "yolo_segv4.pt")
        # YOLOv8-pose 모델 파일 경로
        self.YOLO_POSE_MODEL_PATH = os.path.join(self.MODELS_DIR, "yolov8n-pose.pt")
        # (선택 사항) 마커 감지용 모델 파일 경로 (예: ArUco 마커 감지 모델)
        self.ARUCO_MARKER_MODEL_PATH = os.path.join(self.MODELS_DIR, "aruco_marker_model.pt") # 실제 모델 파일명으로 변경

        # 현재 IDS 서버의 동작 모드: 'object_detect' 또는 'marker_detect'
        self.DETECTOR_CURRENT_MODE = "object_detect" 

        # -----------------------------------------------------------
        # 3. 트래커 설정 (Tracker Settings)
        # -----------------------------------------------------------
        # OC-SORT 트래커가 객체를 몇 프레임 동안 추적하지 못하면 'lost' 상태로 간주하고 추적을 중단할지
        self.TRACKER_LOST_COUNT_THRESHOLD = 20 # 20프레임 동안 감지 안 되면 트랙 삭제

        # -----------------------------------------------------------
        # 4. 네트워크 설정 (Network Settings)
        # -----------------------------------------------------------
        # 메인 서버의 IP 주소
        self.MAIN_SERVER_IP = "127.0.0.1" 
        
        # UDP 포트
        self.IDS_UDP_PORT = 4000
        # TCP 포트
        self.IDS_TCP_PORT = 5000
        
        # TCP 통신 시 타임아웃 설정 (밀리초). 서버 응답 대기 시간
        self.TCP_COMM_TIMEOUT_MS = 1000 

        # -----------------------------------------------------------
        # 5. 시각화 설정 (Visualization Settings)
        # -----------------------------------------------------------
        # 화면에 IDS 처리 결과를 표시할지 여부
        self.ENABLE_DISPLAY = True     # True: 화면 표시 활성화, False: 화면 표시 비활성화
        
        # 시각화 창에 표시될 각 카메라의 이름
        self.DISPLAY_CAMERA_NAMES = {
            "CAM_A": "RWY CCTV A",
            "CAM_B": "RWY CCTV B"
        }
        
        # 화면에 FPS 정보를 표시할지 여부
        self.DISPLAY_FPS = True        
        # 바운딩 박스를 화면에 표시할지 여부
        self.DISPLAY_BBOX = True       
        # 객체 ID를 화면에 표시할지 여부
        self.DISPLAY_ID = True         
        # 포즈 키포인트를 화면에 표시할지 여부 (YOLO-Pose 사용 시)
        self.DISPLAY_POSE = True       

# 프로젝트의 모든 모듈에서 이 설정 객체에 접근할 수 있도록 인스턴스 생성
settings = Settings()

