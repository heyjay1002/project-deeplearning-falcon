# Pilot GUI - 조종사 음성 인터페이스

SC_07 조종사 요청 자동 응답 시스템의 GUI 구현체입니다.

## 📁 폴더 구조

```
pilot_gui/
├── 📂 audio_io/           # 오디오 입출력 (마이크/스피커)
├── 📂 stt/               # 음성 인식 (Speech-to-Text)
├── 📂 query_parser/      # 요청 분류 및 파싱
├── 📂 request_router/    # 요청 처리 및 라우팅
├── 📂 tts/              # 음성 합성 (Text-to-Speech)
├── 📂 controller/       # 메인 컨트롤러
├── 📂 models/           # 데이터 모델
├── 📂 session_utils/    # 세션 관리
├── 📂 logs/             # 로그 파일
├── 📂 tests/            # 테스트 파일들
│   ├── 📂 stt/          # STT 테스트
│   ├── 📂 memory/       # 메모리 테스트
│   ├── 📂 integration/  # 통합 테스트
│   └── 📂 performance/  # 성능 테스트
├── 📂 utils/            # 유틸리티 도구
├── 📂 docs/             # 문서
├── 📄 requirements.txt  # 의존성 패키지
└── 📄 README.md         # 이 파일
```

## 🚀 주요 기능

### 1. 음성 인식 (STT)
- **엔진**: OpenAI Whisper (Medium 모델)
- **언어**: 영어 (항공 통신)
- **장치**: GPU 우선, CPU 폴백
- **성능**: 실시간의 0.2배 처리 속도

### 2. 요청 분류
- **지원 요청**: 9가지 항공 요청 유형
  - BIRD_RISK_CHECK (조류 위험 확인)
  - RUNWAY_STATUS_CHECK (활주로 상태 확인)
  - FOD_STATUS_CHECK (FOD 확인)
  - SYSTEM_STATUS_CHECK (시스템 상태 확인)
  - EMERGENCY_PROCEDURE (비상 절차)
  - RUNWAY_CLOSURE_REQUEST (활주로 폐쇄 요청)
  - BIRD_ALERT_LEVEL_CHANGE (조류 경보 레벨 변경)
  - LANDING_CLEARANCE_REQUEST (착륙 허가 요청)
  - TAKEOFF_READY (이륙 준비)

### 3. 음성 합성 (TTS)
- **엔진**: pyttsx3
- **언어**: 영어
- **모드**: 동기/비동기 지원

## 🔧 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 시스템 의존성 (Ubuntu/Debian)
```bash
sudo apt install portaudio19-dev
```

### 3. 테스트 실행
```bash
# STT 성능 테스트
python tests/stt/test_improved_recognition.py

# 통합 테스트
python tests/integration/test_voice_controller.py

# 메모리 사용량 확인
python tests/memory/debug_memory_usage.py
```

## 📊 성능 지표

- **STT 정확도**: 80%+ (영어 항공 용어)
- **처리 속도**: 실시간의 0.2배 (GPU 기준)
- **GPU 메모리**: ~3GB (Medium 모델)
- **신뢰도**: 0.7+ (양호)

## 🛠️ 개발 도구

### 테스트
- `tests/stt/`: STT 엔진 테스트
- `tests/integration/`: 전체 워크플로우 테스트
- `tests/performance/`: 성능 벤치마크
- `tests/memory/`: 메모리 사용량 분석

### 유틸리티
- `utils/clear_gpu_memory.py`: GPU 메모리 정리

## 📝 사용 예시

```python
from controller.voice_interaction_controller import VoiceInteractionController

# 컨트롤러 초기화
controller = VoiceInteractionController()

# 음성 처리
result = controller.process_voice_request()
print(f"응답: {result.response_text}")
```

## 🔍 문제 해결

### GPU 메모리 부족
```bash
python utils/clear_gpu_memory.py
```

### STT 성능 저하
- Medium → Base 모델로 변경
- CPU → GPU 장치 변경 확인

### 의존성 문제
```bash
pip install --upgrade torch whisper pyaudio pyttsx3
```

## 📚 추가 문서

- `docs/README.md`: 상세 기술 문서
- `docs/old_readme.md`: 이전 버전 문서 