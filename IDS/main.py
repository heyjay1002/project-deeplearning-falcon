# main.py

import cv2
import multiprocessing
import queue 
import json
import time
from config.config import settings 
from camera.camera_worker import CameraWorker 
from inference.detector import Detector 
from transport.tcp_communicator import TcpCommunicator
from transport.udp_streamer import UdpStreamer

# Visualizer는 설정에 따라 조건부로 임포트하고 초기화합니다.
visualizer_instance = None 
if settings.ENABLE_DISPLAY:
    try:
        from utils.visualizer import Visualizer 
        visualizer_instance = Visualizer(settings) 
        print("Display enabled. Press 'q' to quit the application.")
    except ImportError as e:
        print(f"Warning: Could not import Visualizer. Display disabled. Error: {e}")
        settings.ENABLE_DISPLAY = False 
    
if not settings.ENABLE_DISPLAY: 
    print("Display disabled via config.py.")

def main():
    print("IDS Main process started.")
    
    # 1. 카메라 프로세스용 큐 및 워커 생성
    camera_queues = {}
    camera_workers = {}
    for cam_id, dev_path in settings.CAMERA_DEVICES.items(): # 'CAM_A', 'CAM_B'
        q = multiprocessing.Queue(maxsize=settings.CAMERA_QUEUE_MAX_SIZE)
        camera_queues[dev_path] = q
        display_name = settings.DISPLAY_CAMERA_NAMES.get(cam_id, cam_id)
        worker = CameraWorker(dev_path, display_name, q)
        camera_workers[dev_path] = worker 
        worker.start() 
        print(f"Started CameraWorker for {display_name} ({dev_path})")

    # 2. 통신 모듈용 큐 생성
    tcp_send_queue = queue.Queue()
    udp_frame_queue = queue.Queue()

    # 3. 추론 및 통신 모듈 인스턴스 생성
    detector = Detector(settings) 
    tcp_communicator = TcpCommunicator(tcp_send_queue) # main_app_instance 제거
    udp_streamer = UdpStreamer(udp_frame_queue)
    
    # 4. 통신 스레드 시작
    tcp_communicator.start()
    udp_streamer.start()

    last_fps_time = time.time()
    frame_counts = {path: 0 for path in settings.CAMERA_DEVICES.values()} 
    current_fps = {path: 0.0 for path in settings.CAMERA_DEVICES.values()} 

    try:
        while True:
            processed_frames_data = {} 
            for dev_path, q in camera_queues.items():
                try:
                    frame_data = q.get_nowait()
                    processed_frames_data[dev_path] = frame_data
                    frame_counts[dev_path] += 1
                except queue.Empty:
                    pass 

            current_time = time.time()
            if current_time - last_fps_time >= 2.0: 
                for dev_path in settings.CAMERA_DEVICES.values():
                    current_fps[dev_path] = frame_counts[dev_path] / (current_time - last_fps_time)
                    frame_counts[dev_path] = 0 
                last_fps_time = current_time 

            for dev_path, frame_data in processed_frames_data.items():
                frame, img_id = frame_data 
                
                # dev_path로부터 논리적 ID ('CAM_A')를 찾음
                logical_cam_id = next((c_id for c_id, d_p in settings.CAMERA_DEVICES.items() if d_p == dev_path), "Unknown")

                results = detector.track(frame, mode=settings.DETECTOR_CURRENT_MODE)
                tracked_objects = results.get('tracked_objects', [])
                
                # (A) TCP용 JSON 이벤트 생성 (detector가 만들어준 pose 정보를 그대로 사용)
                if tracked_objects:
                    event_message = {
                        "type": "event",
                        "event": "object_detected",
                        "camera_id": logical_cam_id.replace("CAM_", ""), # 'A' 또는 'B'
                        "img_id": img_id,
                        "detections": tracked_objects # detector가 완벽하게 가공한 리스트를 그대로 사용
                    }
                    tcp_send_queue.put(event_message)

                # (B) 시각화 및 UDP용 프레임 준비
                display_frame = frame.copy()
                if settings.ENABLE_DISPLAY and visualizer_instance: 
                    display_frame = visualizer_instance.draw_all_overlays(
                        display_frame,
                        results.get('detections', []),    
                        tracked_objects, 
                        logical_cam_id,    
                        current_fps[dev_path], 
                        results.get('poses', [])
                    )
                    cv2.imshow(logical_cam_id, display_frame)
                
                # (C) UDP 큐에 프레임 추가 (API 스펙에 맞는 짧은 ID 전송)
                udp_frame_queue.put((display_frame, img_id, logical_cam_id.replace("CAM_", "")))

            if settings.ENABLE_DISPLAY and (cv2.waitKey(1) & 0xFF == ord('q')):
                break
            elif not settings.ENABLE_DISPLAY:
                time.sleep(0.001)
    finally:
        print("Terminating all threads and processes...")
        if tcp_communicator.is_alive(): tcp_communicator.stop()
        if udp_streamer.is_alive(): udp_streamer.stop()
        for worker in camera_workers.values(): worker.stop()
        
        if tcp_communicator.is_alive(): tcp_communicator.join(timeout=2)
        if udp_streamer.is_alive(): udp_streamer.join(timeout=2)
        for worker in camera_workers.values(): worker.join(timeout=2)
        
        if settings.ENABLE_DISPLAY: cv2.destroyAllWindows() 
        print("IDS Main process finished.")

if __name__ == '__main__':
    main()