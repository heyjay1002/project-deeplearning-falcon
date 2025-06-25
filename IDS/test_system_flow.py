# test_system_flow.py

import cv2
import numpy as np
from config import Settings
from detector import Detector
import time

def main():
    settings = Settings()
    detector = Detector(settings)

    # 비디오 소스 (웹캠 또는 파일 경로)
    cap = cv2.VideoCapture(settings.CAMERA_PATH)
    if not cap.isOpened():
        print(f"카메라를 열 수 없습니다: {settings.CAMERA_PATH}")
        return

    print("통합 시스템 흐름 테스트를 시작합니다. 'q'를 누르면 종료됩니다.")
    
    homography_matrix = None # 보정 전에는 H 행렬이 없음

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            time.sleep(1)
            continue
        
        # 설정된 해상도로 리사이즈
        frame = cv2.resize(frame, settings.PROCESS_RESOLUTION)
        display_frame = frame.copy()

        # 1. 보정(Calibration) 단계
        if homography_matrix is None:
            # 아직 보정이 안된 상태이므로, Map 모드를 실행
            calibration_result = detector.process_map_mode(frame)
            
            if calibration_result:
                # 보정 성공! H 행렬 저장 및 시각화
                homography_matrix = np.array(calibration_result['matrix'])
                print("✅ [보정 성공] Homography Matrix가 계산되었습니다.")

                # 디버그 플래그가 켜져 있으면, 보정 결과를 프레임에 그림
                display_frame = detector.visualize_calibration_on_frame(display_frame, homography_matrix)
            else:
                # 보정 실패 시 메시지 표시
                cv2.putText(display_frame, "CALIBRATION FAILED: Check ArUco Markers", 
                            (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 2. 객체 탐지(Object Detection) 단계
        else:
            # 보정이 완료된 상태이므로, Object 모드를 실행
            object_result = detector.process_object_mode(frame, time.time_ns())

            if object_result and object_result.get("detections"):
                for det in object_result["detections"]:
                    # 각 객체의 bbox를 프레임에 그림
                    x1, y1, x2, y2 = det["bbox"]
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    
                    # 객체의 하단 중앙점을 기준으로 실제 mm 좌표 계산 (디버깅용)
                    bottom_center_pixel = ((x1 + x2) / 2, y2)
                    world_coords = detector.transform_pixel_to_world(bottom_center_pixel, homography_matrix)
                    
                    # 화면에 정보 표시
                    label = f"{det['class']} ID:{det['object_id']} "
                    label += f"({int(world_coords[0])}, {int(world_coords[1])})mm"
                    cv2.putText(display_frame, label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # 보정이 완료되었음을 시각적으로 계속 표시
            display_frame = detector.visualize_calibration_on_frame(display_frame, homography_matrix)


        # 3. 최종 결과 화면에 표시
        cv2.imshow("FALCON IDS - System Flow Test", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("테스트가 종료되었습니다.")

if __name__ == "__main__":
    main()