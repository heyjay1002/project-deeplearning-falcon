# detector.py

import cv2
import numpy as np
import time
import os
from ultralytics import YOLO
# [수정] 쓰러짐 판단 로직을 bbox 비율 기반으로 변경하고, 해당 함수만 import
from utils import bbox_iou, generate_our_id, estimate_by_bbox_ratio

class Detector:
    def __init__(self, settings):
        self.settings = settings
        
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

    def process_map_mode(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict)

        if ids is None or len(ids) < 4:
            return None
        id_corner_map = {int(id[0]): c for id, c in zip(ids, corners)}
        if not all(i in id_corner_map for i in range(4)):
            return None
        image_points = np.array([id_corner_map[i][0].mean(axis=0) for i in range(4)])
        world_points = np.array(self.settings.ARUCO_WORLD_CORNERS, dtype=np.float32)

        try:
            homography, _ = cv2.findHomography(image_points, world_points)
            if homography is None: return None
        except Exception as e:
            print(f"[ArUco] Homography 오류: {e}")
            return None
        pixel_dist = np.linalg.norm(image_points[0] - image_points[1])
        real_dist = np.linalg.norm(world_points[0] - world_points[1])
        scale = real_dist / pixel_dist

        return {
            "type": "event", "event": "map_calibration", "camera_id": self.settings.CAMERA_ID,
            "matrix": homography.tolist(), "scale": float(scale)
        }
    
    def process_object_mode(self, frame, img_id):
        try:
            results = self.model.track(frame, persist=True, conf=self.settings.YOLO_CONFIDENCE_THRESHOLD, iou=self.settings.YOLO_IOU_THRESHOLD, tracker=self.settings.TRACKER_CONFIG_FILE, verbose=self.settings.YOLO_VERBOSE)[0]
        except Exception as e:
            print(f"YOLO 추론 오류: {e}")
            return None

        if not results.boxes or results.boxes.id is None: return None
        
        boxes, track_ids, classes, confs = results.boxes.xyxy.cpu().numpy(), results.boxes.id.cpu().numpy(), results.boxes.cls.cpu().numpy(), results.boxes.conf.cpu().numpy()
        detections, pose_debug_data = [], []

        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i]
            track_id, cls_id = int(track_ids[i]), int(classes[i])
            cls_name = self.settings.CLASS_NAMES.get(cls_id, str(cls_id))
            bbox = [int(x1), int(y1), int(x2), int(y2)]
            
            crop = frame[int(y1):int(y2), int(x1):int(x2)]
            if crop.size > 0:
                if cls_name == "PERSON":
                    # [수정] 새로운 작업자 탐지 로직을 호출
                    if self.is_wearing_vest(crop):
                        cls_name = "WORK_PERSON"
                elif cls_name == "VEHICLE":
                    if self.is_vehicle_color(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)):
                        cls_name = "WORK_VEHICLE"

            self.object_id_map.setdefault(cls_name, {}); 
            our_id = self.object_id_map[cls_name].setdefault(track_id, generate_our_id(track_id))
            
            rescue_level = None
            if cls_name in ["PERSON", "WORK_PERSON"]:
                # [수정] bbox 비율 기반의 쓰러짐 판단 로직을 호출
                status = estimate_by_bbox_ratio(bbox)
                rescue_level = self.update_fall_level(status, our_id)
                # [수정] bbox 기반으로 변경되었으므로 포즈 디버깅 데이터는 비활성화
                pose_debug_data.append({"bbox": bbox, "is_fallen": int(rescue_level) > 0})
            
            det = {"object_id": our_id, "class": cls_name, "bbox": bbox, "confidence": float(round(confs[i], 2))}
            if rescue_level is not None:
                det["rescue_level"] = str(rescue_level)
            detections.append(det)

        if not detections: return None
        
        return {
            "type": "event", "event": "object_detected", "camera_id": self.settings.CAMERA_ID,
            "img_id": img_id, "detections": detections, "pose_debug_data": pose_debug_data 
        }

    # [수정] 새로운 형광조끼 탐지 함수
    def is_wearing_vest(self, crop_img):
        """
        바운딩 박스 상위 60% 영역에서 형광(주황/노랑) 조끼를 탐지합니다.
        """
        if crop_img.size == 0:
            return False
        
        try:
            h, w, _ = crop_img.shape
            
            # 세로로 긴 바운딩 박스를 가정하고 상위 60%만 ROI로 지정
            roi_upper_h = int(h * 0.6)
            roi = crop_img[0:roi_upper_h, 0:w]
            
            if roi.size == 0:
                return False

            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            total_mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)
            
            # config에 정의된 모든 형광색 범위에 대해 마스크 생성
            for color_name, (lower, upper) in self.settings.VEST_HSV_RANGES.items():
                mask = cv2.inRange(hsv_roi, np.array(lower), np.array(upper))
                total_mask = cv2.bitwise_or(total_mask, mask)

            # ROI 영역 내에서 형광색 픽셀의 비율 계산
            vest_pixel_ratio = np.count_nonzero(total_mask) / total_mask.size
            
            # 비율이 10% 이상일 때 조끼를 입은 것으로 판단 (이 값은 실험을 통해 튜닝 가능)
            return vest_pixel_ratio > 0.1

        except Exception as e:
            if self.settings.DISPLAY_DEBUG:
                print(f"Vest detection error: {e}")
            return False

    def is_vehicle_color(self, hsv_img):
        try:
            yellow_mask = cv2.inRange(hsv_img, np.array(self.settings.VEHICLE_YELLOW_LOWER), np.array(self.settings.VEHICLE_YELLOW_UPPER))
            black_mask = cv2.inRange(hsv_img, np.array(self.settings.VEHICLE_BLACK_LOWER), np.array(self.settings.VEHICLE_BLACK_UPPER))
            return (np.count_nonzero(yellow_mask) / yellow_mask.size > 0.05) and (np.count_nonzero(black_mask) / black_mask.size > 0.01)
        except:
            return False
        
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
    
    def draw_pose_debug(self, frame, keypoints, bbox, is_fallen):
        # [참고] 현재 쓰러짐 감지가 bbox 기반이므로 이 함수는 직접 호출되지 않지만,
        # 향후 포즈 기반 로직이 다시 필요할 경우를 위해 남겨둘 수 있습니다.
        SKELETON_CONNECTIONS = [
            (0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
        ]
        vis_frame = frame
        kpts = keypoints.astype(int)
        for start_idx, end_idx in SKELETON_CONNECTIONS:
            p_start = (kpts[start_idx, 0], kpts[start_idx, 1])
            p_end = (kpts[end_idx, 0], kpts[end_idx, 1])
            if p_start[0] > 0 and p_start[1] > 0 and p_end[0] > 0 and p_end[1] > 0:
                cv2.line(vis_frame, p_start, p_end, (255, 255, 0), 2)
        for px, py in kpts:
            if px > 0 and py > 0:
                cv2.circle(vis_frame, (px, py), 4, (0, 0, 255), -1)
        status = "FALLEN" if is_fallen else "STAND"
        status_color = (0, 0, 255) if is_fallen else (0, 255, 0)
        cv2.putText(vis_frame, f"POSE: {status}", (bbox[0], bbox[1] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        return vis_frame

    def visualize_calibration_on_frame(self, frame, homography_matrix):
        if not self.settings.DEBUG_SHOW_ZONES: return frame
        try:
            H_inv = np.linalg.inv(homography_matrix)
        except np.linalg.LinAlgError:
            return frame
        vis_frame = frame.copy()
        for name, world_corners in self.settings.WORLD_ZONES.items():
            world_points = np.array([world_corners], dtype=np.float32)
            pixel_points = cv2.perspectiveTransform(world_points, H_inv)
            if pixel_points is not None:
                zone_color = self.settings.ZONE_COLORS.get(name, (128, 128, 128))
                overlay = vis_frame.copy()
                cv2.fillPoly(overlay, [pixel_points.astype(np.int32)], zone_color)
                alpha = self.settings.ZONE_OVERLAY_ALPHA 
                vis_frame = cv2.addWeighted(overlay, alpha, vis_frame, 1 - alpha, 0)
                text_pos = np.mean(pixel_points[0], axis=0).astype(int)
                cv2.putText(vis_frame, name, (text_pos[0]-20, text_pos[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        return vis_frame

    def transform_pixel_to_world(self, pixel_point, homography_matrix):
        px, py = pixel_point
        pixel_point_np = np.array([[[px, py]]], dtype=np.float32)
        world_point = cv2.perspectiveTransform(pixel_point_np, homography_matrix)
        return world_point[0][0]