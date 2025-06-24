# camera.py

import cv2
import socket
import time
import numpy as np

class FPSMeter:
    def __init__(self):
        self.last_time = time.time()
        self.frame_count = 0
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

def CameraWorker(inference_queue, settings):
    cam_id = settings.CAMERA_ID
    cam_index = settings.CAMERA_PATH

    #  UDP 소켓 준비
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = (settings.MAIN_SERVER_IP, settings.IDS_UDP_PORT)

    #  카메라 초기화
    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
    if settings.CAMERA_USE_MJPG:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAPTURE_RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAPTURE_RESOLUTION[1])
    cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)

    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return

    print("📷 CameraWorker started.")
    fps_meter = FPSMeter()
    last_udp_log_time = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ 프레임을 읽을 수 없습니다.")
            continue

        #  리사이즈
        frame_resized = cv2.resize(frame, settings.PROCESS_RESOLUTION)
        img_id = time.time_ns()

        #  추론용 큐에 삽입
        if not inference_queue.full():
            inference_queue.put((frame_resized.copy(), img_id))


        #  UDP 전송
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), settings.JPEG_QUALITY]
        ret, jpg_buf = cv2.imencode(".jpg", frame_resized, encode_param)
        if ret:
            try:
                payload = f"{cam_id}:{img_id}:".encode("utf-8") + jpg_buf.tobytes() + b"\n"
                udp_sock.sendto(payload, server_addr)
                if settings.DISPLAY_DEBUG:
                    print(f"[{cam_id}] UDP 전송됨: img_id={img_id}, 크기={len(jpg_buf)}")
            except Exception as e:
                now = time.time()
                if now - last_udp_log_time > 5:
                    print(f"⚠️ UDP 전송 실패: {e}")
                    last_udp_log_time = now

        #  FPS 출력
        if fps_meter.update():
            print(f"[{cam_id}] 📸 FPS: {fps_meter.get():.2f}")