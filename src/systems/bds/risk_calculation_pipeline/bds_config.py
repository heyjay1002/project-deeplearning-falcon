"""
실시간 BDS 파이프라인을 위한 설정값
"""

# --- 일반 설정 ---
UNITY_CAPTURE_DIR = 'unity_capture'
CAMERA_COUNT = 2
CAMERA_LETTERS = ['A', 'B']
FPS_TARGET = 30
MAX_QUEUE_SIZE = 10
OUTPUT_DIR = 'data/realtime_results'

# --- 모델 및 탐지 설정 ---
MODEL_PATH = 'auto'  # 'auto'로 설정 시 최신 모델을 감지, 또는 직접 경로 지정
CONFIDENCE_THRESHOLD = 0.4

# --- 기능 활성화/비활성화 ---
ENABLE_VISUALIZATION = True
ENABLE_RISK_CALCULATION = True
ENABLE_TCP = True

# --- 성능 설정 ---
FRAME_SKIP = 2  # N 프레임마다 1 프레임씩 처리

# --- 위험도 계산 설정 ---
DISTANCE_THRESHOLD = 100  # 근접한 새 떼를 병합하는 임계값

# --- 세션 추적 설정 ---
SESSION_TIMEOUT = 30  # 세션 타임아웃 (프레임 단위)
TRACKING_MODE = 'realtime'  # 'realtime' 또는 'episode'
TRACKING_CONFIG = {
    'position_jump_threshold': 50.0,
    'jump_duration_threshold': 3,
    'min_episode_length': 10,
    'enable_data_cleaning': True,
    'realtime_mode': True
}

# --- TCP 연결 설정 ---
TCP_HOST = 'localhost'
TCP_PORT = 5200
