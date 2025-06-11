import cv2
import multiprocessing
import queue 
import time
from config.config import settings 
from camera.camera_worker import CameraWorker 
from inference.detector import Detector 

# Visualizer는 설정에 따라 조건부로 임포트하고 초기화합니다.
visualizer_instance = None 
if settings.ENABLE_DISPLAY:
    try:
        from utils.visualizer import Visualizer 
        visualizer_instance = Visualizer(settings) 
        print("Display enabled. Press 'q' to quit the application.")
    except ImportError as e:
        print(f"Warning: Could not import Visualizer module. Display will be disabled. Error: {e}")
        settings.ENABLE_DISPLAY = False 
    
if not settings.ENABLE_DISPLAY: 
    print("Display disabled via config.py.")

def main():
    print("IDS Main process started.")
    
    camera_queues = {}
    camera_workers = {}
    
    # config.settings.CAMERA_DEVICES 딕셔너리를 순회하며 카메라 워커를 생성하고 시작합니다.
    for logical_camera_id, device_path in settings.CAMERA_DEVICES.items():
        cam_queue = multiprocessing.Queue(maxsize=settings.CAMERA_QUEUE_MAX_SIZE)
        camera_queues[device_path] = cam_queue 

        display_name = settings.DISPLAY_CAMERA_NAMES.get(logical_camera_id, logical_camera_id)

        worker = CameraWorker(device_path, display_name, cam_queue)
        camera_workers[device_path] = worker 
        
        worker.start() 
        print(f"Started CameraWorker for {display_name} ({device_path})")

    detector = Detector(settings) 
    
    last_fps_time = time.time()
    frame_counts = {path: 0 for path in settings.CAMERA_DEVICES.values()} 
    current_fps = {path: 0.0 for path in settings.CAMERA_DEVICES.values()} 

    while True:
        processed_frames_data = {} 

        for device_path, cam_queue in camera_queues.items():
            try:
                frame_data = cam_queue.get(timeout=0.01) 
                processed_frames_data[device_path] = frame_data
                frame_counts[device_path] += 1
            except queue.Empty:
                pass 

        current_time = time.time()
        if current_time - last_fps_time >= 2.0: 
            for device_path in settings.CAMERA_DEVICES.values():
                current_fps[device_path] = frame_counts[device_path] / (current_time - last_fps_time)
                frame_counts[device_path] = 0 
            last_fps_time = current_time 

        for device_path, frame_data in processed_frames_data.items():
            frame, img_id = frame_data 
            
            logical_id_found = None
            for lid, d_path in settings.CAMERA_DEVICES.items():
                if d_path == device_path:
                    logical_id_found = lid
                    break
            display_name = settings.DISPLAY_CAMERA_NAMES.get(logical_id_found, logical_id_found)

            detection_and_track_results = detector.track(frame, mode=settings.DETECTOR_CURRENT_MODE)
            
            detections = detection_and_track_results.get('detections', [])
            tracked_objects = detection_and_track_results.get('tracked_objects', []) 
            poses = detection_and_track_results.get('poses', [])

            if settings.ENABLE_DISPLAY: 
                display_frame = visualizer_instance.draw_all_overlays(
                    frame.copy(),  
                    detections,    
                    tracked_objects, 
                    display_name,    
                    current_fps[device_path], 
                    poses            
                )
                cv2.imshow(display_name, display_frame) 

        if settings.ENABLE_DISPLAY:
            key = cv2.waitKey(1) & 0xFF 
            if key == ord('q'): 
                print("Q pressed, exiting main loop...")
                break 
        else:
            time.sleep(0.01) 

    print("Terminating CameraWorkers...")
    for worker in camera_workers.values():
        worker.stop() 
    for worker in camera_workers.values():
        worker.join() 
    
    if settings.ENABLE_DISPLAY: 
        cv2.destroyAllWindows() 
    
    print("IDS Main process finished.")

if __name__ == '__main__':
    main()