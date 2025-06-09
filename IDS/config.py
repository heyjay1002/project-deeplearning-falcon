from pathlib import Path

#  기본 디렉토리 설정 (이 파일 기준 루트 디렉토리)
BASE_DIR = Path(__file__).resolve().parent  # /IDS 기준

# 카메라 장치 인덱스 설정
CAMERA_CONFIG = {
    "A": 0,  # /dev/video0
    "B": 2   # /dev/video2 (상황에 따라 다를 수 있음)
}

# YOLO 모델 경로 설정 (상대경로 → 절대경로로 변환)
YOLO_MODEL_PATH = BASE_DIR / "technical_test" / "dl_model_test" / "object_detecting" / "single_model" / "yolo8s_seg" / "all_fine_fune_v1" / "weights" / "best.pt"

# 맵 정보 JSON 경로 (좌표 보정용)(예시)
MAP_CONFIG_PATH = BASE_DIR / "map" / "config" / "runway_map.json"

# 로그 디렉토리(예시)
LOG_DIR = BASE_DIR / "logs"

# 후처리 파라미터(예시)
POSTPROCESSING = {
    "vest_color_range": {
        "lower": [20, 100, 100],  # HSV 범위 (예: 노란 조끼)
        "upper": [30, 255, 255]
    },
    "yellow_vehicle_range": {
        "lower": [15, 100, 100],
        "upper": [35, 255, 255]
    }
}

# 트래커 설정(예시)
TRACKER_CONFIG = {
    "max_age": 30,
    "min_hits": 3,
    "iou_threshold": 0.3
}
