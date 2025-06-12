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
    if not settings.ENABLE_INFERENCE:
        print("="*50 + "\n>>> WARNING: Model inference is DISABLED via config.py. <<<\n" + "="*50)

    camera_queues = {}
    camera_workers = {}
    for cam_id, dev_path in settings.CAMERA_DEVICES.items():
        q = multiprocessing.Queue(maxsize=settings.CAMERA_QUEUE_MAX_SIZE)
        camera_queues[dev_path] = q
        display_name = settings.DISPLAY_CAMERA_NAMES.get(cam_id, cam_id)
        worker = CameraWorker(dev_path, display_name, q)
        camera_workers[dev_path] = worker 
        worker.start() 
        print(f"Started CameraWorker for {display_name} ({dev_path})")

    tcp_send_queue = queue.Queue()
    udp_frame_queue = queue.Queue()

    detector = Detector(settings) 
    tcp_communicator = TcpCommunicator(tcp_send_queue)
    udp_streamer = UdpStreamer(udp_frame_queue)
    
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
                except queue.Empty: pass 

            current_time = time.time()
            if current_time - last_fps_time >= 2.0: 
                if settings.LOG_FPS_TO_CONSOLE:
                    print("-" * 50)
                    for dev_path in settings.CAMERA_DEVICES.values():
                        fps = frame_counts[dev_path] / (current_time - last_fps_time)
                        logical_cam_id = next((c_id for c_id, d_p in settings.CAMERA_DEVICES.items() if d_p == dev_path), "Unknown")
                        print(f"--- [Main Loop] Cam {logical_cam_id} Processing FPS: {fps:.2f} ---")
                        current_fps[dev_path] = fps
                    print("-" * 50)
                for dev_path in settings.CAMERA_DEVICES.values(): frame_counts[dev_path] = 0
                last_fps_time = current_time 

            for dev_path, frame_data in processed_frames_data.items():
                frame, img_id = frame_data 
                logical_cam_id = next((c_id for c_id, d_p in settings.CAMERA_DEVICES.items() if d_p == dev_path), "Unknown")
                api_cam_id = logical_cam_id.replace("CAM_", "")

                if settings.ENABLE_INFERENCE:
                    results = detector.track(frame, mode=settings.DETECTOR_CURRENT_MODE)
                else:
                    results = {'tracked_objects': [], 'poses': [], 'detections': []}
                
                tracked_objects = results.get('tracked_objects', [])
                if tracked_objects:
                    event_message = {
                        "type": "event", "event": "object_detected",
                        "camera_id": api_cam_id, "img_id": img_id,
                        "detections": tracked_objects
                    }
                    if settings.LOG_FPS_TO_CONSOLE:
                        print(f"\n--- Event Generated for TCP (CAM {api_cam_id}) ---")
                        print(json.dumps(event_message, indent=2, ensure_ascii=False))
                    tcp_send_queue.put(event_message)

                display_frame = frame.copy()
                if settings.ENABLE_DISPLAY and visualizer_instance: 
                    if settings.ENABLE_INFERENCE:
                        display_frame = visualizer_instance.draw_all_overlays(
                            display_frame, results.get('detections', []), tracked_objects, 
                            logical_cam_id, current_fps[dev_path], results.get('poses', [])
                        )
                    cv2.imshow(logical_cam_id, display_frame)
                
                udp_frame_queue.put((display_frame, img_id, api_cam_id))

            if settings.ENABLE_DISPLAY and (cv2.waitKey(1) & 0xFF == ord('q')): break
            elif not settings.ENABLE_DISPLAY: time.sleep(0.001)
                
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