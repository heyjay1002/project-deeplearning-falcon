# detector.py

import cv2
import numpy as np
import time
import os
from ultralytics import YOLO
from utils import bbox_iou, generate_our_id, estimate_pose_status

class Detector:
    def __init__(self, settings):
        self.settings = settings
        
        # 모델 경로 확인
        detect_model_path = self.settings.DETECTING_MODEL_PATH
        pose_model_path = self.settings.MODEL_PATH_POSE
        
        if not os.path.exists(detect_model_path):
            raise FileNotFoundError(f"Detection model not found: {detect_model_path}")
        if not os.path.exists(pose_model_path):
            raise FileNotFoundError(f"Pose model not found: {pose_model_path}")
            
        print(f"Loading detection model: {detect_model_path}")
        print(f"Loading pose model: {pose_model_path}")
        
        self.model = YOLO(detect_model_path)
        self.pose_model = YOLO(pose_model_path)
        self.last_fall_time = {}
        self.object_id_map = {} 


    # 맵 보정 모드 
    def process_map_mode(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict)

        if ids is None or len(ids) < 4:
            if self.settings.DISPLAY_DEBUG:
                print(f"[ArUco] 마커 부족: {len(ids) if ids is not None else 0}/4")
            return None
        # ID가 0, 1, 2, 3인 마커의 코너를 추출
        id_corner_map = {int(id[0]): corner for id, corner in zip(ids, corners)}
        if not all(i in id_corner_map for i in range(4)):
            if self.settings.DISPLAY_DEBUG:
                print(f"[ArUco] 필요한 ID 부족: {list(id_corner_map.keys())}")
            return None
        # 각 마커의 중심 좌표 계산
        image_points = np.array([id_corner_map[i][0].mean(axis=0) for i in range(4)])

        # 각 마커의 실제 좌표 설정
        world_points = np.array(self.settings.ARUCO_WORLD, dtype=np.float32)

        # Homography 계산
        try:
            homography, _ = cv2.findHomography(image_points, world_points)
            if homography is None:
                print("[ArUco] Homography 계산 실패")
                return None
        except Exception as e:
            print(f"[ArUco] Homography 오류: {e}")
            return None
        # 스케일 계산
        pixel_dist = np.linalg.norm(image_points[0] - image_points[1])
        real_dist = np.linalg.norm(world_points[0] - world_points[1])
        scale = real_dist / pixel_dist

        if self.settings.DISPLAY_DEBUG:
            print("[ArUco] Homography matrix:", homography)
            print("[ArUco] Scale:", scale)

        return {
            "type": "event",
            "event": "map_calibration",
            "camera_id": self.settings.CAMERA_ID,
            "matrix": homography.tolist(),
            "scale": scale
        }
    
    # 객체 감지 모드
    def process_object_mode(self, frame, img_id):
        try:
            results = self.model.track(
                frame,
                persist=True,
                conf=self.settings.YOLO_CONFIDENCE_THRESHOLD,
                iou=self.settings.YOLO_IOU_THRESHOLD,
                tracker=self.settings.TRACKER_CONFIG_FILE,
                verbose=False
            )[0]
        except Exception as e:
            print(f"YOLO 추론 오류: {e}")
            return None

        if not results.boxes or results.boxes.id is None:
            return None

        boxes = results.boxes.xyxy.cpu().numpy()
        track_ids = results.boxes.id.cpu().numpy()
        classes = results.boxes.cls.cpu().numpy()
        confidences = results.boxes.conf.cpu().numpy()

        detections = []
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i]
            track_id = int(track_ids[i])
            cls_id = int(classes[i])
            conf = float(confidences[i])
            cls_name = self.settings.CLASS_NAMES.get(cls_id, str(cls_id))

            bbox = [int(x1), int(y1), int(x2), int(y2)]

            # ArUco 마스크 필터링 (설정에 따라)
            if hasattr(self.settings, 'ENABLE_ARUCO_MASK_FILTER') and self.settings.ENABLE_ARUCO_MASK_FILTER:
                if hasattr(self.settings, 'ARUCO_MASK_BBOX'):
                    if any(bbox_iou(bbox, marker_bbox) > 0 for marker_bbox in self.settings.ARUCO_MASK_BBOX):
                        continue

            # HSV 분석
            try:
                crop = frame[int(y1):int(y2), int(x1):int(x2)]
                if crop.size > 0:
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

                    if cls_name == "PERSON" and self.is_vest_present(hsv):
                        cls_name = "WORK_PERSON"
                    elif cls_name == "VEHICLE" and self.is_vehicle_color(hsv):
                        cls_name = "WORK_VEHICLE"
            except Exception as e:
                if self.settings.DISPLAY_DEBUG:
                    print(f"HSV 분석 오류: {e}")

            # track_id 기반 ID 생성
            self.object_id_map.setdefault(cls_name, {})
            if track_id not in self.object_id_map[cls_name]:
                self.object_id_map[cls_name][track_id] = generate_our_id(track_id)
            our_id = self.object_id_map[cls_name][track_id]

            # 쓰러짐 감지
            rescue_level = None
            if cls_name in ["PERSON", "WORK_PERSON"]:
                try:
                    pose_result = self.pose_model(frame)[0]
                    status = estimate_pose_status(pose_result)
                    rescue_level = self.update_fall_level(status, our_id)
                except Exception as e:
                    if self.settings.DISPLAY_DEBUG:
                        print(f"포즈 추정 오류: {e}")
                    rescue_level = 0

            det = {
                "object_id": our_id,
                "class": cls_name,
                "bbox": bbox,
                "confidence": round(conf, 2)
            }
            if rescue_level is not None:
                det["rescue_level"] = str(rescue_level)

            detections.append(det)

        if not detections:
            return None

        return {
            "type": "event",
            "event": "object_detected",
            "camera_id": self.settings.CAMERA_ID,
            "img_id": img_id,
            "detections": detections
        }
    
    # 형광조끼 유무 판단
    def is_vest_present(self, hsv_img):
        try:
            mask = cv2.inRange(hsv_img, np.array(self.settings.VEST_HSV_LOWER), np.array(self.settings.VEST_HSV_UPPER))
            ratio = np.count_nonzero(mask) / mask.size
            return ratio > 0.1
        except:
            return False

    # 차량 색상 판단
    def is_vehicle_color(self, hsv_img):
        try:
            yellow_mask = cv2.inRange(hsv_img, np.array(self.settings.VEHICLE_YELLOW_LOWER), np.array(self.settings.VEHICLE_YELLOW_UPPER))
            black_mask = cv2.inRange(hsv_img, np.array(self.settings.VEHICLE_BLACK_LOWER), np.array(self.settings.VEHICLE_BLACK_UPPER))
            return (np.count_nonzero(yellow_mask) / yellow_mask.size > 0.05) and \
                   (np.count_nonzero(black_mask) / black_mask.size > 0.01)
        except:
            return False
        
    # 쓰러짐 레벨 업데이트
    def update_fall_level(self, pose_status, object_id):
        now = time.time()
        key = f"{self.settings.CAMERA_ID}_{object_id}"

        if pose_status == "FALLEN":
            if key not in self.last_fall_time:
                self.last_fall_time[key] = now
                return 1
            elapsed = now - self.last_fall_time[key]
            return min(int(elapsed) + 1, self.settings.RESCUE_LEVEL_MAX)
        else:
            self.last_fall_time.pop(key, None)
            return 0
        

    def visualize_calibration_on_frame(self, frame, homography_matrix):
        """
        [디버깅용] 계산된 호모그래피 행렬이 정확한지 확인하기 위해,
        실제 세계 좌표계의 구역들을 원본 이미지 위에 투영하여 그립니다.
        """
        if not self.settings.DEBUG_VISUALIZE_CALIBRATION:
            return frame
        
        try:
            H_inv = np.linalg.inv(homography_matrix)
        except np.linalg.LinAlgError:
            return frame

        vis_frame = frame.copy()

        for name, world_corners in self.settings.WORLD_ZONES.items():
            world_points = np.array([world_corners], dtype=np.float32)
            pixel_points = cv2.perspectiveTransform(world_points, H_inv)

            if pixel_points is not None:
                overlay = vis_frame.copy()
                cv2.fillPoly(overlay, [pixel_points.astype(np.int32)], (0, 255, 0))
                alpha = 0.3
                vis_frame = cv2.addWeighted(overlay, alpha, vis_frame, 1 - alpha, 0)
                
                text_pos = np.mean(pixel_points[0], axis=0).astype(int)
                cv2.putText(vis_frame, name, (text_pos[0]-20, text_pos[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return vis_frame

    # [추가 2] 픽셀 좌표 -> 실제 mm 좌표 변환 함수
    def transform_pixel_to_world(self, pixel_point, homography_matrix):
        """
        한 개의 픽셀 좌표를 실제 세계 좌표(mm)로 변환합니다.
        """
        px, py = pixel_point
        pixel_point_np = np.array([[[px, py]]], dtype=np.float32)
        
        world_point = cv2.perspectiveTransform(pixel_point_np, homography_matrix)
        
        return world_point[0][0]