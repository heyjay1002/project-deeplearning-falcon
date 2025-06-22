# FALCON - Deep Learning Aviation System

항공 관제 및 조종사 지원을 위한 AI 기반 시스템

## 🚁 Pilot GUI

조종사용 음성 인터페이스 - 활주로 상태 확인 및 조류 위험도 평가

### 실행 방법

```bash
# pilot_gui 폴더에서 실행
cd gui/pilot_gui
python main.py
```

### 주요 기능

- 🎤 **음성 인식**: Whisper 기반 STT
- 🧠 **요청 분류**: Ollama LLM 기반 의도 파악
- 🗣️ **음성 합성**: pyttsx3 기반 TTS
- 🛬 **활주로 상태**: 실시간 활주로 정보 제공
- 🐦 **조류 위험도**: 조류 활동 모니터링

## 📁 프로젝트 구조

```
dl-falcon/
├── gui/
│   ├── pilot_gui/          # 조종사용 GUI
│   │   ├── main.py         # 메인 실행 파일
│   │   ├── stt/            # 음성 인식
│   │   ├── query_parser/   # 요청 분석
│   │   ├── tts/            # 음성 합성
│   │   ├── audio_io/       # 오디오 입출력
│   │   └── controller/     # GUI 컨트롤러
│   └── atc_gui/            # 관제사용 GUI
└── README.md
```

## 🔧 설치 및 설정

```bash
# 의존성 설치
cd gui/pilot_gui
pip install -r requirements.txt

# Ollama 설치 및 모델 다운로드
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b
```

![Screenshot from 2025-06-02 23-33-12](https://github.com/user-attachments/assets/3792ca68-67eb-465f-a0cf-677b4572b339)

# FALCON: 딥러닝 기반 비행장 안전 대응 시스템
> Foreign object Auto-detection & Localization Camera Observation Network
