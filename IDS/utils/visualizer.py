import cv2
import numpy as np
from config.config import settings # 설정값을 가져오기 위해 임포트

class Visualizer:
    """
    딥러닝 추론 결과와 시스템 정보를 영상 프레임에 오버레이하여 시각화하는 클래스입니다.
    개발 및 디버깅 목적으로 사용되며, config 설정을 통해 활성화/비활성화 및 세부 제어가 가능합니다.
    """
    def __init__(self, config_settings):
        """
        Visualizer를 초기화합니다.
        Args:
            config_settings: config.py의 settings 객체 (시각화 관련 설정 포함).
        """
        # config_settings 객체 전체를 저장하여 필요한 시각화 설정을 직접 참조합니다.
        self.config = config_settings 
        
        # 글꼴 설정 (모든 그리기 함수에서 공통으로 사용)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_info = 1.0 # FPS, 카메라 이름 등 정보 텍스트 크기
        self.font_scale_bbox = 0.5 # 바운딩 박스 위 ID/클래스 텍스트 크기
        self.thickness = 2         # 선 굵기/텍스트 굵기

        # 색상 정의 (BGR 형식)
        self.color_text_info = (0, 255, 255) # 노란색 (FPS, 카메라 이름 등)
        self.color_bbox = (0, 255, 0)      # 초록색 (바운딩 박스)
        self.color_id = (255, 0, 0)        # 파란색 (ID)
        self.color_pose = (0, 0, 255)      # 빨간색 (포즈 키포인트)
        # self.color_mask = (0, 255, 255)    # 마스크 색상 (이제 필요 없음)

    def draw_boxes_and_ids(self, frame: np.ndarray, detections: list, tracked_objects: list) -> np.ndarray:
        """
        프레임에 바운딩 박스와 객체 ID를 그립니다.
        Args:
            frame: 원본 이미지 프레임 (numpy.ndarray)
            detections: 탐지된 객체 리스트
            tracked_objects: 추적된 객체 리스트
        Returns:
            바운딩 박스와 ID가 그려진 프레임 (numpy.ndarray)
        """
        # 바운딩 박스나 ID 표시가 비활성화되어 있으면 그리지 않고 원본 프레임 반환
        if not self.config.DISPLAY_BBOX and not self.config.DISPLAY_ID:
            return frame 

        # -------------------------------------------------------------
        # 1. 세그멘테이션 마스크 그리기 로직 제거
        # -------------------------------------------------------------
        # 이전 코드에 있던 마스크 그리기 로직은 여기에서 제거되었습니다.
        
        # -------------------------------------------------------------
        # 2. 바운딩 박스와 객체 ID 그리기
        # -------------------------------------------------------------
        # 추적된 객체 정보를 기반으로 그리는 것이 더 안정적입니다.
        for obj in tracked_objects:
            x1, y1, x2, y2 = map(int, obj.get('bbox', [0,0,0,0]))
            object_id = obj.get('object_id', 'N/A')
            obj_class = obj.get('class', 'unknown')
            conf = obj.get('confidence', 0.0)

            # 바운딩 박스 그리기
            if self.config.DISPLAY_BBOX:
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.color_bbox, self.thickness)

            # ID와 클래스, 신뢰도 정보 텍스트
            if self.config.DISPLAY_ID:
                text = f"ID:{object_id} {obj_class} ({conf:.1f})"
                # 텍스트 배경을 위한 사각형 그리기 (가독성 향상)
                (text_width, text_height), baseline = cv2.getTextSize(text, self.font, self.font_scale_bbox, self.thickness)
                # 텍스트 배경 사각형이 프레임 밖으로 나가지 않도록 조정
                text_y = max(y1 - text_height - baseline, 0) # y 좌표가 0보다 작아지지 않도록
                cv2.rectangle(frame, (x1, y1 - text_height - baseline), (x1 + text_width, y1), self.color_id, -1) # -1은 채우기
                cv2.putText(frame, text, (x1, text_y + text_height), self.font, self.font_scale_bbox, (255, 255, 255), self.thickness) # 흰색 텍스트

        return frame

    def draw_fps_info(self, frame: np.ndarray, fps_value: float, camera_name: str) -> np.ndarray:
        """
        프레임에 FPS 정보를 그립니다.
        Args:
            frame: 원본 이미지 프레임 (numpy.ndarray)
            fps_value: 현재 FPS 값
            camera_name: 카메라의 표시 이름
        Returns:
            FPS 정보가 그려진 프레임 (numpy.ndarray)
        """
        if not self.config.DISPLAY_FPS: 
            return frame 

        text = f"{camera_name} FPS: {fps_value:.2f}"
        # 텍스트 위치 (좌측 상단)
        cv2.putText(frame, text, (10, 30), self.font, self.font_scale_info, self.color_text_info, self.thickness)
        return frame

    def draw_keypoints(self, frame: np.ndarray, poses: list) -> np.ndarray:
        """
        프레임에 포즈 키포인트를 그립니다.
        Args:
            frame: 원본 이미지 프레임 (numpy.ndarray)
            poses: 포즈 키포인트 정보 리스트. 형식: [{'keypoints': [[x,y], ...], 'bbox': [...]}, ...]
        Returns:
            키포인트가 그려진 프레임 (numpy.ndarray)
        """
        if not self.config.DISPLAY_POSE:
            return frame 

        for pose_data in poses:
            keypoints = pose_data['keypoints']
            # bbox = pose_data['bbox'] # 포즈의 바운딩 박스 (필요시 사용)

            # 키포인트 그리기
            for kp in keypoints:
                x, y = int(kp[0]), int(kp[1])
                cv2.circle(frame, (x, y), 3, self.color_pose, -1) 
            
            # (선택 사항) 관절 연결선 그리기 (YOLO-Pose의 특정 키포인트 인덱스 필요)
            # COCO 데이터셋의 경우:
            # connections = [
            #     (0, 1), (0, 2), (1, 3), (2, 4), # Head/Shoulders
            #     (5, 6), (5, 7), (6, 8), (7, 9), (8, 10), # Arms
            #     (11, 12), (11, 13), (12, 14), (13, 15), (14, 16) # Legs
            # ]
            # for start_idx, end_idx in connections:
            #     if len(keypoints) > max(start_idx, end_idx) and all(keypoints[start_idx]) and all(keypoints[end_idx]):
            #         pt1 = (int(keypoints[start_idx][0]), int(keypoints[start_idx][1]))
            #         pt2 = (int(keypoints[end_idx][0]), int(keypoints[end_idx][1]))
            #         cv2.line(frame, pt1, pt2, self.color_pose, self.thickness // 2)

        return frame

    def draw_all_overlays(self, frame: np.ndarray, detections: list, tracked_objects: list, 
                           camera_name: str, fps_value: float = None, poses: list = None) -> np.ndarray:
        """
        모든 시각화 오버레이를 한 번에 그립니다.
        Args:
            frame: 원본 이미지 프레임
            detections: 탐지 결과 (bbox, class, conf, mask)
            tracked_objects: 추적 결과 (id, bbox, class, conf)
            camera_name: 카메라 이름 문자열
            fps_value: 현재 FPS 값 (선택 사항)
            poses: 포즈 키포인트 정보 (선택 사항)
        Returns:
            모든 정보가 그려진 프레임
        """
        # 마스크 그리기 로직이 제거되었으므로, detections 리스트에서 mask 정보는 더 이상 사용되지 않습니다.
        # draw_boxes_and_ids 함수는 바운딩 박스와 ID를 그립니다.
        frame = self.draw_boxes_and_ids(frame, detections, tracked_objects)
        
        # 포즈 키포인트 그리기
        if poses is not None and len(poses) > 0: 
            frame = self.draw_keypoints(frame, poses)
        
        # FPS 정보 그리기
        if fps_value is not None: 
            frame = self.draw_fps_info(frame, fps_value, camera_name)
            
        return frame