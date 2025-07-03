# inference.py

import time
import json
import numpy as np
from detector import Detector

# [추가] NumPy 객체를 JSON으로 안전하게 변환하기 위한 커스텀 인코더
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super(NumpyEncoder, self).default(obj)

def InferenceWorker(inference_queue, tcp_queue, mode_queue, settings):
    print("🧠 InferenceWorker started.")

    detector = Detector(settings)
    current_mode = "map"
    last_log_time = 0

    while True:
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
            
            if mode_changed:
                response_msg = {
                    "type": "response",
                    "command": cmd,
                    "result": "ok"
                }
                tcp_queue.put(response_msg)

        if inference_queue.empty():
            time.sleep(0.01)
            continue
            
        frame, img_id = inference_queue.get()

        if current_mode == "map":
            result = detector.process_map_mode(frame)
            if result:
                tcp_queue.put(result)

        elif current_mode == "object":
            result = detector.process_object_mode(frame, img_id)
            if result:
                # [핵심] 로그 출력과 TCP 전송 로직 수정
                now = time.time()
                if now - last_log_time > 5:
                    # 로그용 데이터는 복사해서 사용하고, 커스텀 인코더로 안전하게 출력
                    log_result = result.copy()
                    if "pose_debug_data" in log_result:
                        del log_result["pose_debug_data"] # 로그에서는 디버그 정보 제외
                    print(f"[{settings.CAMERA_ID}] 감지 결과: {json.dumps(log_result, cls=NumpyEncoder, ensure_ascii=False)}")
                    last_log_time = now

                # [매우 중요] 서버로 보내기 전, 디버깅용 데이터를 '반드시' 삭제
                if "pose_debug_data" in result:
                    del result["pose_debug_data"]
                
                tcp_queue.put(result) # 깨끗하게 정제된 데이터만 서버로 전송