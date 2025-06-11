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

    def draw_boxes_and_ids(self, frame: np.ndarray, detections: list, tracked_objects: list) -> np.ndarray:
        """
        프레임에 바운딩 박스와 객체 ID를 그립니다. (다음 단계에서 구현 예정)
        Args:
            frame: 원본 이미지 프레임 (numpy.ndarray)
            detections: 탐지된 객체 리스트
            tracked_objects: 추적된 객체 리스트
        Returns:
            바운딩 박스와 ID가 그려진 프레임 (numpy.ndarray)
        """
        # 현재 단계에서는 구현하지 않습니다. 다음 단계 (Detector/Tracker 구현 후)에서 채워넣습니다.
        # if self.config.DISPLAY_BBOX or self.config.DISPLAY_ID:
        #     # 여기에 바운딩 박스, ID 그리는 로직 추가
        pass # Placeholder for future implementation
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
        if not self.config.DISPLAY_FPS: # config 설정에 따라 FPS 표시 여부 결정
            return frame 

        text = f"{camera_name} FPS: {fps_value:.2f}"
        # 텍스트 위치 (좌측 상단)
        cv2.putText(frame, text, (10, 30), self.font, self.font_scale_info, self.color_text_info, self.thickness)
        return frame

    def draw_keypoints(self, frame: np.ndarray, poses: list) -> np.ndarray:
        """
        프레임에 포즈 키포인트를 그립니다. (다음 단계에서 구현 예정)
        Args:
            frame: 원본 이미지 프레임 (numpy.ndarray)
            poses: 포즈 키포인트 정보 리스트
        Returns:
            키포인트가 그려진 프레임 (numpy.ndarray)
        """
        # 현재 단계에서는 구현하지 않습니다. 다음 단계 (Detector/Tracker 구현 후)에서 채워넣습니다.
        # if self.config.DISPLAY_POSE:
        #     # 여기에 키포인트 그리는 로직 추가
        pass # Placeholder for future implementation
        return frame

    def draw_all_overlays(self, frame: np.ndarray, detections: list, tracked_objects: list, 
                           camera_name: str, fps_value: float = None, poses: list = None) -> np.ndarray:
        """
        모든 시각화 오버레이를 한 번에 그립니다.
        Args:
            frame: 원본 이미지 프레임
            detections: 탐지 결과 (bbox, class, conf) - 현재 단계에서는 빈 리스트
            tracked_objects: 추적 결과 (id, bbox, class) - 현재 단계에서는 빈 리스트
            camera_name: 카메라 이름 문자열
            fps_value: 현재 FPS 값 (선택 사항)
            poses: 포즈 키포인트 정보 (선택 사항) - 현재 단계에서는 None
        Returns:
            모든 정보가 그려진 프레임
        """
        # draw_boxes_and_ids는 현재 비어있으므로 바로 frame을 반환합니다.
        frame = self.draw_boxes_and_ids(frame, detections, tracked_objects)
        
        # poses가 None이 아니고, 표시 활성화 상태일 때만 호출 (현재 poses는 None)
        if poses is not None: 
            frame = self.draw_keypoints(frame, poses)
        
        if fps_value is not None: # FPS 값이 있을 때만 호출하여 그립니다.
            frame = self.draw_fps_info(frame, fps_value, camera_name)
            
        return frame