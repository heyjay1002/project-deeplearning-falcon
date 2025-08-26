"""
RedWing 인터페이스의 주요 설정값
"""

# --- 서버 및 네트워크 설정 ---
DEFAULT_HOST = "localhost"
PDS_SERVER_PORT = 5000
BDS_SERVER_PORT = 5001
IDS_SERVER_PORT = 5002
MAIN_SERVER_PORT = 5300 # create_voice_controller의 기본 포트

# --- 오디오 설정 ---
DEFAULT_RECORDING_DURATION = 5.0

# --- STT (Speech-to-Text) 엔진 설정 ---
STT_MODEL_NAME = "small"  # Whisper 모델 크기 (e.g., tiny, base, small, medium, large)
STT_LANGUAGE = "en"
STT_DEVICE = "auto"  # "cuda", "cpu", "auto"

# --- TTS (Text-to-Speech) 엔진 설정 ---
TTS_USE_COQUI = True
TTS_COQUI_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"
TTS_FALLBACK_TO_PYTTSX3 = True
TTS_DEVICE = "cuda"  # "cuda" 또는 "cpu"

# --- 기타 기본값 ---
DEFAULT_CALLSIGN = "UNKNOWN"
