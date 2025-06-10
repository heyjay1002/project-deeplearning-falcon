import cv2
import multiprocessing
import queue
import time
from config.config import settings # config.py에서 설정 임포트

def CameraWorker(multiprocessing.Process):
    def __init__(self, camera_path: str, output_queue: multiprocessing.Queue):
        super().__init__()

        self.camera_path = camera_path      # 웹캠 장치 경로
        self.output_queue = output_queue    # 캡처된 프레임을 전달할 큐
        self.stop_event = multiprocessing.Event()   # 프로세스 종료를 위한 이벤트 플래그

        # 카메라 설정은 config.py에서 가져옴
        self.width = settings.