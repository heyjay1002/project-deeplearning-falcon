# inference.py

import time
import json
import numpy as np
from detector import Detector

def InferenceWorker(inference_queue, tcp_queue, mode_queue, settings):
    print("🧠 InferenceWorker started.")

    detector = Detector(settings)  # settings 전달
    current_mode = "map"  # 초기 모드: map
    last_log_time = 0

    while True:
        # 감지 모드 전환 확인
        while not mode_queue.empty():
            cmd = mode_queue.get()
            mode_changed = False
            
            if cmd == "set_mode_map":
                current_mode = "map"
                print("🔁 감지 모드 변경 → map")
                mode_changed = True
            elif cmd == "set_mode_object":
                current_mode = "object"
                print("🔁 감지 모드 변경 → object")
                mode_changed = True
            
            # 모드 변경이 성공했을 경우, 서버로 응답 메시지를 전송
            if mode_changed:
                response_msg = {
                    "type": "response",
                    "command": cmd,
                    "result": "ok"
                }
                tcp_queue.put(response_msg)

        # 프레임 수신
        if inference_queue.empty():
            time.sleep(0.01)
            continue
            
        frame, img_id = inference_queue.get()

        # 모드에 따른 분기 처리
        if current_mode == "map":
            result = detector.process_map_mode(frame)
            if result:
                tcp_queue.put(result)

        elif current_mode == "object":
            result = detector.process_object_mode(frame, img_id)
            if result:
                tcp_queue.put(result)
                
                # 로그 출력
                now = time.time()
                if now - last_log_time > 5:
                    print(f"[{settings.CAMERA_ID}] 감지 결과: {json.dumps(result, ensure_ascii=False)}")
                    last_log_time = now