import torch
from ultralytics import YOLO 
import numpy as np
import cv2 
from config.config import settings

class Detector:
    """
    딥러닝 모델(YOLO)을 로드하고, 입력 프레임에 대해 객체 감지, 추적, 
    인스턴스 세그멘테이션, 포즈 추정 등을 수행하는 클래스입니다.
    """
    def __init__(self, model_settings): 
        """
        Detector를 초기화하고 YOLO 모델들을 로드합니다.
        Args:
            model_settings: config.py의 settings 객체 (모델 관련 설정 포함).
        """
        self.detecting_model = None # 객체 감지 및 추적 (YOLOv11seg-m)
        self.pose_model = None      # 자세 추정 (YOLO-Pose)
        self.aruco_detector = None  # ArUco 마커 감지기 (현재 주석 처리)

        # 1. YOLO Detecting 모델 로드 (yolov11seg-m.pt)
        try:
            self.detecting_model = YOLO(model_settings.YOLO_DETECTING_MODEL_PATH)
            self.detecting_model.to('cuda') # 모델을 GPU로 이동
            print(f"[Detector] YOLO Detecting model loaded successfully: {model_settings.YOLO_DETECTING_MODEL_PATH}")
        except Exception as e:
            print(f"Error loading YOLO Detecting model from {model_settings.YOLO_DETECTING_MODEL_PATH}: {e}")
            self.detecting_model = None 

        # 2. YOLO-Pose 모델 로드 (yolov8n-pose.pt)
        try:
            self.pose_model = YOLO(model_settings.YOLO_POSE_MODEL_PATH)
            self.pose_model.to('cuda')
            print(f"[Detector] YOLO-Pose model loaded successfully: {model_settings.YOLO_POSE_MODEL_PATH}")
        except Exception as e:
            print(f"Error loading YOLO-Pose model from {model_settings.YOLO_POSE_MODEL_PATH}: {e}")
            self.pose_model = None

        # 3. ArUco 마커 감지기 초기화 (필요시 주석 해제하여 사용)
        # self.aruco_detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250))
        # print("[Detector] ArUco detector initialized.")

    def track(self, frame: np.ndarray, mode: str = "object_detect") -> dict:
        """
        입력 프레임에 대해 딥러닝 추론 및 내장 추적을 수행하고 결과를 반환합니다.
        메인 함수에서 `detector.track()`으로 호출됩니다.
        Args:
            frame: NumPy 배열 형태의 이미지 프레임.
            mode: 현재 Detector의 동작 모드 ("object_detect" 또는 "marker_detect").
        Returns:
            딕셔너리 형태로 감지 및 추적 결과를 반환합니다.
            'detections': 원본 탐지 결과 리스트 (bbox, class, conf, mask 포함 가능)
            'tracked_objects': 추적된 객체 리스트 (bbox, object_id, class, conf 포함)
            'poses': 감지된 사람의 자세 정보 리스트 (keypoints, bbox 포함)
            'markers': 감지된 마커 정보 리스트 (marker_id, position 포함)
        """
        results = {
            'detections': [], 
            'tracked_objects': [], 
            'poses': [],
            'markers': []
        }

        # 프레임의 실제 크기 (높이, 너비)를 가져옵니다.
        frame_height, frame_width = frame.shape[:2]
        # 전체 이미지 면적 (픽셀)을 계산합니다.
        total_frame_area = frame_width * frame_height
        # 바운딩 박스가 차지할 수 있는 최대 허용 면적 (전체 면적의 절반, 50%)을 설정합니다.
        max_bbox_area_ratio = 0.5 # 50% 제한
        max_allowed_bbox_area = total_frame_area * max_bbox_area_ratio


        if mode == "object_detect":
            # 객체 감지 및 포즈 추정 모델이 모두 로드되지 않았다면 경고 출력
            if self.detecting_model is None and self.pose_model is None: 
                print("[Detector] Warning: No object or pose models loaded for 'object_detect' mode.")
                return results

            # 1. YOLO Detecting 모델을 사용한 객체 감지 및 추적 (FOD, Person 등)
            detected_persons_bboxes = [] # 포즈 추정을 위해 사람의 바운딩 박스를 저장할 리스트
            
            if self.detecting_model: # Detecting 모델이 로드되었다면
                try:
                    # --- 전처리 로직 추가 ---
                    # 전처리는 모델 추론 전에 한 번만 적용됩니다.
                    processed_frame = frame.copy() # 원본 프레임 복사
                    
                    # CLAHE 적용 (빛 반사 완화 및 대비 향상)
                    # 그레이스케일로 변환 후 CLAHE 적용, 다시 BGR로 변환
                    gray_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)) # 파라미터 조절
                    equalized_gray = clahe.apply(gray_frame)
                    processed_frame = cv2.cvtColor(equalized_gray, cv2.COLOR_GRAY2BGR) 
                    
                    # 감마 보정 예시 (주석 해제 시 사용)
                    # gamma = 0.8 # 1보다 작으면 밝아지고, 1보다 크면 어두워짐
                    # gamma_corrected_frame = np.array(255 * (processed_frame / 255.0) ** gamma, dtype=np.uint8)
                    # processed_frame = gamma_corrected_frame

                    # 블러 적용 예시 (작은 노이즈 제거, 주석 해제 시 사용)
                    # processed_frame = cv2.GaussianBlur(processed_frame, (5, 5), 0)
                    # --- 전처리 로직 끝 ---

                    # ultralytics의 track() 메서드를 사용하여 내장 추적 기능을 활성화합니다.
                    track_results = self.detecting_model.track(processed_frame, persist=True, conf=0.15, iou=0.7, verbose=False) 
                    
                    for r in track_results: # 각 추론 결과 객체(Result 객체) 순회
                        boxes = r.boxes.xyxy.cpu().numpy() 
                        classes = r.boxes.cls.cpu().numpy() 
                        confidences = r.boxes.conf.cpu().numpy() 
                        masks = r.masks.data.cpu().numpy() if r.masks else None 
                        
                        if r.boxes.id is not None: # 추적 ID가 있는 경우
                            track_ids = r.boxes.id.cpu().numpy()
                            
                            for i in range(len(boxes)): # 감지된 각 객체에 대해
                                x1, y1, x2, y2 = boxes[i]
                                
                                # --- 앵커 박스 크기 제한 로직 추가 ---
                                # 바운딩 박스의 너비와 높이 계산
                                bbox_width = x2 - x1
                                bbox_height = y2 - y1
                                # 바운딩 박스의 면적 계산
                                bbox_area = bbox_width * bbox_height

                                # 바운딩 박스 면적이 허용된 최대 면적을 초과하는지 확인
                                if bbox_area > max_allowed_bbox_area:
                                    # print(f"Skipping large bbox: {bbox_area:.2f} (Max allowed: {max_allowed_bbox_area:.2f})")
                                    continue # 해당 바운딩 박스는 건너뛰고 다음으로 넘어갑니다.
                                # --- -------------------------- ---

                                cls = self.detecting_model.names[int(classes[i])] 
                                conf = float(confidences[i])
                                obj_id = int(track_ids[i]) 

                                if cls == 'person': 
                                    detected_persons_bboxes.append([x1, y1, x2, y2]) 

                                results['tracked_objects'].append({
                                    'bbox': [x1, y1, x2, y2],
                                    'object_id': obj_id,
                                    'class': cls,
                                    'confidence': conf
                                })
                                detection_info = {
                                    'bbox': [x1, y1, x2, y2],
                                    'class': cls,
                                    'confidence': conf
                                }
                                if masks is not None:
                                    detection_info['mask'] = masks[i]
                                results['detections'].append(detection_info) 
                        else: # 추적 ID가 없는 경우
                            for i in range(len(boxes)):
                                x1, y1, x2, y2 = boxes[i]
                                
                                # --- 앵커 박스 크기 제한 로직 추가 (추적 ID 없는 경우에도 적용) ---
                                bbox_width = x2 - x1
                                bbox_height = y2 - y1
                                bbox_area = bbox_width * bbox_height
                                if bbox_area > max_allowed_bbox_area:
                                    # print(f"Skipping large bbox: {bbox_area:.2f} (Max allowed: {max_allowed_bbox_area:.2f})")
                                    continue 
                                # --- -------------------------------------------------------- ---

                                cls = self.detecting_model.names[int(classes[i])] 
                                conf = float(confidences[i])
                                detection_info = {
                                    'bbox': [x1, y1, x2, y2],
                                    'class': cls,
                                    'confidence': conf
                                }
                                if masks is not None:
                                    detection_info['mask'] = masks[i]
                                results['detections'].append(detection_info)

                except Exception as e:
                    print(f"[Detector] Error during YOLO Detecting tracking: {e}") 

            # 2. YOLO-Pose 추론 (사람이 감지되었을 때만 실행)
            # self.pose_model이 로드되어 있고, detected_persons_bboxes에 사람이 감지되었을 때만
            if self.pose_model and len(detected_persons_bboxes) > 0: 
                try:
                    # pose 모델은 track()을 지원하지 않을 수 있으므로 predict() 사용
                    # pose 모델에도 전처리된 프레임을 전달하는 것이 일관적입니다.
                    pose_results = self.pose_model.predict(processed_frame, conf=0.5, verbose=False) # <-- processed_frame 전달
                    for r in pose_results: 
                        if r.keypoints and hasattr(r.keypoints, 'xy') and len(r.keypoints.xy) > 0: 
                            keypoints_xy = r.keypoints.xy.cpu().numpy()
                            boxes_pose = r.boxes.xyxy.cpu().numpy()
                            
                            for i in range(len(keypoints_xy)):
                                # --- 포즈 바운딩 박스에도 크기 제한 적용 ---
                                # YOLO-Pose의 bbox는 이미 추론된 것이므로, 여기서도 필터링 가능
                                x1_p, y1_p, x2_p, y2_p = boxes_pose[i]
                                bbox_width_p = x2_p - x1_p
                                bbox_height_p = y2_p - y1_p
                                bbox_area_p = bbox_width_p * bbox_height_p
                                if bbox_area_p > max_allowed_bbox_area:
                                    continue # 너무 큰 포즈 바운딩 박스는 건너뜀
                                # --- ----------------------------------- ---

                                results['poses'].append({
                                    'keypoints': keypoints_xy[i].tolist(), 
                                    'bbox': boxes_pose[i].tolist() 
                                })
                except Exception as e:
                    print(f"[Detector] Error during YOLO-Pose prediction: {e}")

        elif mode == "marker_detect":
            if self.aruco_detector is None:
                print("[Detector] Warning: ArUco detector not initialized for 'marker_detect' mode.")
                return results
            
            pass

        return results