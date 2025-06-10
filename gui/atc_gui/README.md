## 개발 환경
- Ubuntu 24.04
- PyQt6
- Python 3.12

## 관제사 GUI 디렉토리 구조
```plain
falcon_gui/
├── requirements.txt 
├── main.py                      # 실행 진입점
├── config/
│   └──  settings.py             # 설정값, 상수 정의(포트, IP 등)
├── ui/                          # Qt Designer 기반 UI 클래스
│   ├── main_window.ui           # Main 창 전체 레이아웃 UI
│   ├── main_page.ui             # 위험도/지도/리스트 통합 UI
│   ├── access_page.ui           # 출입 조건 설정 페이지
│   ├── log_page.ui              # 이력 조회 페이지
│   ├── object_detail_dialog.ui  # 객체 상세 보기 다이얼로그
│   └── alert_popup.ui           # 알림 팝업 UI
├── pages/                       # 페이지별 UI 로직 클래스
│   ├── main_page.py
│   ├── access_page.py
│   ├── log_page.py
│   └── object_detail_dialog.py
├── models/                      # 데이터 모델 정의
│   ├── detected_object.py
│   ├── alarm_data.py
│   ├── restriction_setting.py
│   └── log_record.py
├── utils/
│   ├── tcp_client.py
│   ├── udp_client.py
│   ├── interface.py             # signal 포함 인터페이스 클래스
│   ├── data_validator.py        # 데이터 유효성 검증
│   └── logger.py
├── resources/
│   ├── images/
│   ├── sounds/
│   └── styles/
└── tests/
    ├── test_main.py
    └── test_tcp_udp_mock.py
 
```
