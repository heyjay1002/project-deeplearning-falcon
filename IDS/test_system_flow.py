# test_system_flow.py

import cv2
import numpy as np
from config import Settings
from detector import Detector
import time
# [수정] utils에서 우리가 만든 3개의 새로운 함수를 모두 import 합니다.
from utils import estimate_by_bbox_ratio, estimate_by_keypoint_std_dev, estimate_by_torso_angle

def main():
    settings = Settings()
    detector = Detector(settings)

    cap = cv2.VideoCapture(settings.CAMERA_PATH)
    if not cap.isOpened():
        print(f"카메라를 열 수 없습니다: {settings.CAMERA_PATH}")
        return

    print("통합 시스템 흐름 테스트를 시작합니다. 'q'를 누르면 종료됩니다.")
    
    homography_matrix = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다."); time.sleep(1); continue
        
        frame = cv2.resize(frame, settings.PROCESS_RESOLUTION)
        display_frame = frame.copy()

        if homography_matrix is None:
            calibration_result = detector.process_map_mode(frame)
            if calibration_result:
                homography_matrix = np.array(calibration_result['matrix'])
                print("✅ [보정 성공] Homography Matrix가 계산되었습니다.")
            if settings.DEBUG_VISUALIZE_CALIBRATION and homography_matrix is not None:
                display_frame = detector.visualize_calibration_on_frame(display_frame, homography_matrix)
            else:
                cv2.putText(display_frame, "CALIBRATION FAILED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            object_result = detector.process_object_mode(frame, time.time_ns())

            if object_result:
                if object_result.get("detections"):
                    for det in object_result["detections"]:
                        x1, y1, x2, y2 = det["bbox"]
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        label = f"{det['class']} ID:{det['object_id']}"
                        cv2.putText(display_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # [핵심] 다중 로직 동시 테스트 및 시각화
                if settings.DEBUG_SHOW_POSE and object_result.get("pose_debug_data"):
                    for pose_info in object_result["pose_debug_data"]:
                        kpts, bbox = pose_info["keypoints"], pose_info["bbox"]
                        
                        # [수정] 각 함수에 필요한 데이터를 직접 전달합니다.
                        status_bbox = estimate_by_bbox_ratio(bbox)
                        status_std = estimate_by_keypoint_std_dev(kpts)
                        status_angle = estimate_by_torso_angle(kpts)
                        
                        # 3. 각 로직의 결과를 화면에 모두 표시
                        results_to_display = {
                            f"BBOX: {status_bbox}": status_bbox == "FALLEN",
                            f"STD_DEV: {status_std}": status_std == "FALLEN",
                            f"ANGLE: {status_angle}": status_angle == "FALLEN"
                        }
                        y_offset = 30
                        for text, is_fallen in results_to_display.items():
                            color = (0, 0, 255) if is_fallen else (0, 255, 0)
                            cv2.putText(display_frame, text, (bbox[0], bbox[1] - y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            y_offset += 25
            
            if settings.DEBUG_SHOW_ZONES:
                display_frame = detector.visualize_calibration_on_frame(display_frame, homography_matrix)

        cv2.imshow("FALCON IDS - Multi-Logic Test", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("테스트가 종료되었습니다.")

if __name__ == "__main__":
    main()