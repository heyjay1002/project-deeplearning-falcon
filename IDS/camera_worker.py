import cv2
import time
from threading import Thread
from queue import Queue
import numpy as np
from ultralytics import YOLO
from ocsort.ocsort import OCSort  # 반드시 OC-SORT 설치 필요
from pathlib import Path
from config import YOLO_MODEL_PATH, CAMERA_CONFIG

# 사용할 모델 경로
model_path="../../../technical_test/dl_model_test/object_detecting/single_model/yolo8s_seg/all_fine_fune_v1/weights/best.pt"
'''
camera_worker  기능
- 카메라로부터 프레임 캡처
- YOLOv8로 객체 감지 수행
- OCSORT로 추적 및 track_id 부여
- 추적 결과를 Queue로 전송
'''
class CameraWorker(Thread):
    def __init__(self, cam_id, output_queue):

        self.cam_id = cam_id              # "A" or "B"
        self.output_queue = output_queue  # 추적 결과를 보낼 큐
        self.cam_index = CAMERA_CONFIG[cam_id]
        self.model = YOLO(str(YOLO_MODEL_PATH))
        self.tracker = OCSort()           # OCSORT 트래커
        self.cap = cv2.VideoCapture(self.cam_index)
        self.stopped = False

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def run(self):
        while not self.stopped:
            frame = self.read_frame()
            if frame is None:
                continue

            results = self.model(frame)[0]
            detections = []

            for box in results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                detections.append([x1, y1, x2, y2, conf, cls_id])

            detections_np = np.array(detections)
            tracks = self.tracker.update(detections_np)

            timestamp = time.time()
            for track in tracks:
                x1, y1, x2, y2, track_id, cls_id = track[:6]
                obj = {
                    "camera": self.cam_id,
                    "track_id": int(track_id),
                    "class_id": int(cls_id),
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "timestamp": timestamp
                }
                self.output_queue.put(obj)

    def stop(self):
        self.stopped = True
        self.cap.release()


# ✅ 사용 예시
if __name__ == "__main__":
    queue_a = Queue()
    cam_a_worker = CameraWorker(cam_id="A", cam_index=0, output_queue=queue_a)
    cam_a_worker.start()

    while True:
        if not queue_a.empty():
            obj = queue_a.get()
            print(obj)
