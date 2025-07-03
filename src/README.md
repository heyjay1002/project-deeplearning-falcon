# FALCON 소스 코드 구조

## 📁 디렉토리 구조

```
src/
├── systems/             # 핵심 시스템 모듈들
│   ├── bds/            # Bird Detection System
│   ├── ids/            # Intrusion Detection System
│   └── tracking/       # 추적 시스템 (향후 개발)
│
├── simulation/         # 시뮬레이션 모듈들
│   ├── bird_sim/       # 새 충돌 시뮬레이션
│   └── runway_sim/     # 활주로 시뮬레이션
│
├── interfaces/         # 사용자 인터페이스
│   ├── hawkeye/        # 관제사용 GUI (PyQt 기반)
│   └── redwing/        # 음성 인터페이스
│
├── infrastructure/     # 시스템 인프라
│   ├── server/         # 서버 관련 코드
│   ├── network/        # 네트워크 통신 (향후 개발)
│   └── database/       # 데이터베이스 관련 (향후 개발)
│
├── shared/             # 공통 모듈들
│   ├── utils/          # 유틸리티 함수들
│   ├── models/         # AI 모델들 (향후 개발)
│   └── protocols/      # 통신 프로토콜 (향후 개발)
│
└── tests/              # 테스트 코드
    └── technical_test/ # 기술 검증 테스트
```

## 🎯 모듈 설명

### Systems (시스템)
- **BDS (Bird Detection System)**: 조류 탐지 및 위험도 계산
- **IDS (Intrusion Detection System)**: 침입 객체 탐지
- **Tracking**: 객체 추적 시스템 (향후 개발)

### Simulation (시뮬레이션)
- **bird_sim**: Unity 기반 새 충돌 시뮬레이션
- **runway_sim**: Unity 기반 활주로 시뮬레이션

### Interfaces (인터페이스)
- **hawkeye**: PyQt 기반 관제사용 GUI - 실시간 모니터링 및 제어
- **redwing**: 음성 기반 인터페이스 - STT/TTS 기반 상호작용

### Infrastructure (인프라)
- **server**: 중앙 서버 및 통신 관리
- **network**: 네트워크 통신 모듈
- **database**: 데이터베이스 연동

### Shared (공통)
- **utils**: ArUco 마커, 웹캠 등 유틸리티
- **models**: AI 모델 관리
- **protocols**: 시스템 간 통신 프로토콜

### Tests (테스트)
- **technical_test**: 딥러닝 모델, STT/TTS 등 기술 검증

## 🚀 사용법

각 모듈은 독립적으로 실행 가능하며, 필요에 따라 통합하여 사용할 수 있습니다.

### 주요 진입점
- `src/interfaces/hawkeye/main.py` - GUI 실행
- `src/interfaces/redwing/redwing_gui.py` - 음성 인터페이스 실행
- `src/systems/bds/main.py` - BDS 시스템 실행
- `src/systems/ids/main.py` - IDS 시스템 실행 