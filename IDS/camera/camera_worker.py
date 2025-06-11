import cv2
import multiprocessing
import queue
import time
from config.config import settings # config.py에서 설정 임포트

class CameraWorker(multiprocessing.Process):

    def __init__(self, camera_path: str, display_name: str, output_queue: multiprocessing.Queue):
        super().__init__()

        self.camera_path = camera_path      # 웹캠 장치 경로
        self.display_name = display_name    # 디버깅 화면 이름
        self.output_queue = output_queue    # 캡처된 프레임을 전달할 큐
        self.stop_event = multiprocessing.Event()   # 프로세스 종료를 위한 이벤트 플래그

        # 카메라 설정은 config.py에서 가져옴
        self.width = settings.CAMERA_RESOLUTION_WIDTH
        self.height = settings.CAMERA_RESOLUTION_HEIGHT
        self.fps = settings.CAMERA_FPS
        self.queue_max_size = settings.CAMERA_QUEUE_MAX_SIZE
        self.drop_oldest_on_full = settings.CAMERA_DROP_OLDEST_ON_FULL  #큐가 가득 찼을때 프레임을 드롭할지 설정

    def run(self):
        print(f"[{self.display_name}] CameraWorker started. Path: {self.camera_path}")
        cap = None

        try:
            cap = cv2.VideoCapture(self.camera_path)
            if not cap.isOpened():
                print(f"Error: [{self.display_name}] Could not open camera {self.camera_path}")
                return

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)

            while not self.stop_event.is_set():
                ret, frame = cap.read()

                if not ret:
                    print(f"[{self.display_name}] Failed to grab frame, retrying...")
                    time.sleep(0.05)
                    continue
                
                current_img_id = time.time_ns() 

                try:
                    if self.output_queue.full() and self.drop_oldest_on_full:
                        self.output_queue.get_nowait()
                    self.output_queue.put((frame, current_img_id,), block=False)

                except queue.Full:
                    pass
                except Exception as e:
                    # --- 이 부분이 핵심 수정입니다! 'diaplay_name'을 'display_name'으로 변경 ---
                    print(f"[{self.display_name}] Error putting frame to queue: {e}") 
                    # --- ---------------------------------------------------------------- ---
        except Exception as e:
            print(f"[{self.display_name}] An unexpected error occurred in run(): {e}")
        finally:
            if cap:
                cap.release()
            print(f"[{self.display_name}] CameraWorker stopped.")

    def stop(self):
        self.stop_event.set()