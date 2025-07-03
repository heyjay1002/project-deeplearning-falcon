# FALCON 소스 코드 구조

## 📁 디렉토리 구조

```
src/
├── systems/             # 핵심 시스템 모듈들
│   ├── bds/            # Bird Detection System
│   └── ids/            # Intrusion Detection System
│
├── simulation/         # 시뮬레이션 모듈들
│   ├── bird_sim/       # 새 충돌 시뮬레이션
│   └── runway_sim/     # 활주로 시뮬레이션
│
├── interfaces/         # 사용자 인터페이스
│   ├── hawkeye/        # 관제사용 GUI
│   └── redwing/        # 조종사용 GUI
│
├── infrastructure/     # 시스템 인프라
│   └──server/         # 서버 관련 코드
│
├── shared/             # 공통 모듈들
│   └── utils/          # 유틸리티 함수들
│
└── tests/              # 테스트 코드
    └── technical_test/ # 기술 검증 테스트
```
