import cv2
import multiprocessing
import queue 
import time
from config.config import settings # config.py에서 설정 객체 임포트
from camera.camera_worker import CameraWorker # CameraWorker 클래스 임포트

def main():
    print("IDS Main process started.")
    # --------------------------------------------------------------------------
    visualizer_instance = None 
    if settings.ENABLE_DISPLAY:
        try:
            from utils.visualizer import Visualizer # Visualizer 클래스 임포트
            visualizer_instance = Visualizer(settings) # Visualizer 초기화 시 settings 객체 전체 전달
            print("Display enabled. Press 'q' to quit the application.")
        except ImportError as e:
            print(f"Warning: Could not import Visualizer module. Display will be disabled. Error: {e}")
            # 임포트 실패 시, 설정된 디스플레이 플래그를 강제로 비활성화
            settings.ENABLE_DISPLAY = False 

    if not settings.ENABLE_DISPLAY: 
        print("Display disabled via config.py.")

    # --------------------------------------------------------------------------
    
    # 각 카메라별 큐와 워커를 저장할 딕셔너리
    camera_queues = {}
    camera_workers = {}

    # config.settings.CAMERA_DEVICES 딕셔너리를 순회하며 워커 생성 및 시작
    for camera_path, display_name in settings.CAMERA_DEVICES.items():
        cam_queue = multiprocessing.Queue(maxsize=settings.CAMERA_QUEUE_MAX_SIZE)
        camera_queues[camera_path] = cam_queue 

        worker = CameraWorker(camera_path, display_name, cam_queue)
        camera_workers[camera_path] = worker 
        
        worker.start() 
        print(f"Started CameraWorker for {display_name} ({camera_path})")

    # Detector 및 Tracker 초기화 (다음 단계에서 구현할 예정입니다.)
    # detector = Detector(settings.MODELS_DIR, ...) 
    # tracker = Tracker(settings.TRACKER_LOST_COUNT_THRESHOLD)

    # FPS 계산을 위한 변수 초기화 (각 카메라별로 관리)
    last_fps_time = time.time()
    frame_counts = {path: 0 for path in settings.CAMERA_DEVICES.keys()} 
    current_fps = {path: 0.0 for path in settings.CAMERA_DEVICES.keys()} 

    # 5. 메인 처리 루프
    while True:
        processed_frames_data = {} 

        # 5.1. 각 카메라 큐에서 프레임 가져오기
        for camera_path, cam_queue in camera_queues.items():
            try:
                frame_data = cam_queue.get(timeout=0.01) 
                processed_frames_data[camera_path] = frame_data
                frame_counts[camera_path] += 1
            except queue.Empty:
                pass 

        # 5.2. FPS 계산 및 업데이트
        current_time = time.time()
        if current_time - last_fps_time >= 1.0: 
            for camera_path in settings.CAMERA_DEVICES.keys():
                current_fps[camera_path] = frame_counts[camera_path] / (current_time - last_fps_time)
                frame_counts[camera_path] = 0 
            last_fps_time = current_time 

        # 5.3. 프레임 처리 (딥러닝 추론, 추적) 및 시각화
        
        for camera_path, frame_data in processed_frames_data.items():
            frame, img_id = frame_data 
            display_name = settings.CAMERA_DEVICES[camera_path] 

            # --- 다음 단계에서 Detector와 Tracker 호출 로직이 여기에 들어갑니다 ---
            detections = [] 
            tracked_objects = [] 
            poses = [] 
            # --- ------------------------------------------------------------- ---

            if settings.ENABLE_DISPLAY: # 설정이 True일 때만 시각화 로직 실행
                display_frame = visualizer_instance.draw_all_overlays(
                    frame.copy(),  
                    detections,    
                    tracked_objects, 
                    display_name,    
                    current_fps[camera_path], 
                    poses            
                )
                cv2.imshow(display_name, display_frame) 

        # 5.4. 키 입력 대기 및 종료 (시각화 활성화 시에만)
        if settings.ENABLE_DISPLAY:
            key = cv2.waitKey(1) & 0xFF 
            if key == ord('q'): 
                print("Q pressed, exiting main loop...")
                break 
        else:
            time.sleep(0.01) 

    # 6. 자원 정리 
    print("Terminating CameraWorkers...")
    for worker in camera_workers.values():
        worker.stop() 
    for worker in camera_workers.values():
        worker.join() 
    
    if settings.ENABLE_DISPLAY: # 시각화가 활성화되었을 때만 창을 닫습니다.
        cv2.destroyAllWindows() 
    
    print("IDS Main process finished.")

if __name__ == '__main__':
    main()