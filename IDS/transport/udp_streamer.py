# transport/udp_streamer.py

import socket
import threading
import queue
import cv2
import time
from config.config import settings

class UdpStreamer(threading.Thread):
    def __init__(self, frame_queue):
        super().__init__()
        self.host = settings.MAIN_SERVER_IP
        self.port = settings.IDS_UDP_PORT
        self.frame_queue = frame_queue
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stop_event = threading.Event()
        self.sent_frames = 0
        self.last_log_time = time.time()

    def run(self):
        print(f"[UDP] Streamer started for {self.host}:{self.port}")
        MAX_UDP_PACKET_SIZE = 65000 

        while not self.stop_event.is_set():
            try:
                frame, img_id, cam_id = self.frame_queue.get(timeout=1)
                
                quality = 90
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                result, encoded_img = cv2.imencode('.jpg', frame, encode_param)

                header = f"{cam_id}:{img_id}:".encode('utf-8')
                message = header + encoded_img.tobytes()

                while len(message) > MAX_UDP_PACKET_SIZE and quality > 10:
                    quality -= 10
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                    result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
                    message = header + encoded_img.tobytes()

                if result and len(message) <= MAX_UDP_PACKET_SIZE:
                    self.sock.sendto(message, (self.host, self.port))
                    self.sent_frames += 1
                else:
                    print(f"[UDP] Frame CAM {cam_id} is too large to send. Skipping.")

                current_time = time.time()
                if current_time - self.last_log_time >= 2.0:
                    if settings.LOG_FPS_TO_CONSOLE:
                        fps = self.sent_frames / (current_time - self.last_log_time)
                        print(f"--- [UDP Stream] Sending FPS: {fps:.2f} ---")
                    self.sent_frames = 0
                    self.last_log_time = current_time
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[UDP] Error streaming frame: {e}")
        print("[UDP] Streamer stopped.")

    def stop(self):
        self.stop_event.set()