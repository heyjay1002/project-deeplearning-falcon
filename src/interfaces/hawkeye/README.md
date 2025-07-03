## 개발 환경
- Ubuntu 24.04
- PyQt6
- Python 3.12

## Hawkeye 디렉토리 구조
```plain
hawkeye/
├── requirements.txt
├── main.py                      # 실행 진입점
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py              # 설정값 정의(포트, IP 등)
│   └── constants.py             # 상수값 정의
├── ui/                          # Qt Designer 기반 UI 파일
│   ├── main_window.ui           # Main 창 전체 레이아웃 UI
│   ├── main_page.ui             # 위험도/지도/리스트 통합 UI
│   ├── access_page.ui           # 출입 조건 설정 페이지
│   ├── log_page.ui              # 이력 조회 페이지
│   ├── log_page_old.ui          # 이전 버전 이력 조회 페이지
│   └── object_detail_dialog.ui  # 객체 상세 보기 다이얼로그
├── views/                       # 페이지별 UI 로직 클래스
│   ├── main_page.py
│   ├── access_page.py
│   ├── log_page.py
│   ├── notification_dialog.py
│   └── object_detail_dialog.py
├── widgets/                     # 커스텀 위젯 클래스
│   ├── __init__.py
│   └── map_marker_widget.py
├── utils/                       # 유틸리티 및 네트워크 관련 모듈
│   ├── __init__.py
│   ├── network_manager.py
│   ├── tcp_client.py
│   ├── udp_client.py
│   ├── interface.py
│   └── logger.py
├── resources/
│   └── images/                  # 이미지 리소스
│       ├── airplane.png
│       ├── ambulance.png
│       ├── ... (생략)
├── logs/                        # 로그 파일 저장 폴더
│   ├── app_YYYYMMDD.log         # 로그 파일들
│   └── ...
└── __init__.py
```
