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
│   ├── atc_gui/        # 관제사용 GUI
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
- **BDS**: 조류 탐지 시스템
- **IDS**: 침입 탐지 시스템  
- **Tracking**: 객체 추적 시스템

### Simulation (시뮬레이션)
- **Bird Sim**: Unity 기반 새 충돌 시뮬레이션
- **Runway Sim**: Unity 기반 활주로 시뮬레이션

### Interfaces (인터페이스)
- **ATC GUI**: 관제사용 PyQt 기반 GUI
- **RedWing**: 음성 명령 인터페이스

### Infrastructure (인프라)
- **Server**: TCP/UDP 통신 서버
- **Network**: 네트워크 통신 모듈
- **Database**: 데이터베이스 연결 및 관리

### Shared (공통)
- **Utils**: 공통 유틸리티 함수들
- **Models**: AI 모델 관리
- **Protocols**: 통신 프로토콜 정의 