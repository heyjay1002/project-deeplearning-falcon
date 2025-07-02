## 개발 환경
- Ubuntu 24.04
- PyQt6
- Python 3.12

## 관제사 GUI 디렉토리 구조
```plain
falcon_gui/
├── requirements.txt (생성 예정)
├── main.py                      # 실행 진입점
├── config/
│   ├── __init__.py 
|   ├── settings.py              # 설정값 정의(포트, IP 등)
│   └── constants.py             # 상수값 정의
├── ui/                          # Qt Designer 기반 UI 클래스
│   ├── main_window.ui           # Main 창 전체 레이아웃 UI
│   ├── main_page.ui             # 위험도/지도/리스트 통합 UI
│   ├── access_page.ui           # 출입 조건 설정 페이지
│   ├── log_page.ui              # 이력 조회 페이지
│   └── object_detail_dialog.ui  # 객체 상세 보기 다이얼로그
├── views/                     # 페이지별 UI 로직 클래스
│   ├── main_page.py
│   ├── access_page.py
│   ├── log_page.py
│   ├── notification_dialog.py
│   └── object_detail_dialog.py
├── models/                      # 데이터 모델 정의
│   ├── detected_object.py
│   ├── bird_runway_risk.py
│   ├── access_setting.py
│   └── log_record.py
├── utils/
│   ├── network_manager.py
│   ├── tcp_client.py
│   ├── udp_client.py
│   ├── interface.py
│   └── logger.py
├── resources/
│   ├── images/
│   ├── sounds/
│   └── styles/
└── tests/
│   └── test_detection_dialog.py

 
```
