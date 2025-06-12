'''
ids_server/
├── config/
│   └── config.py              # 모든 시스템 설정값 (카메라, 모델, 네트워크, 시각화 등)을 파이썬 변수로 관리
│
├── camera/
│   ├── __init__.py            # Python 패키지 인식용 (비워 둬도 됨)
│   └── camera_worker.py       # 각 웹캠으로부터 프레임을 비동기 캡처하고 큐에 전달 (별도 Process)
│
├── inference/
│   ├── __init__.py
│   ├── detector.py            # YOLOv11seg-m, YOLO-Pose 모델 로딩 및 객체/자세 추론 (모드 전환 로직 포함)
│   └── tracker.py             # OC-SORT 추적 알고리즘 (bbox 기반)
│
├── transport/
│   ├── __init__.py
│   ├── udp_streamer.py        # H.264 영상 스트림을 Main Server로 UDP 전송
│   └── tcp_communicator.py    # Main Server와의 TCP 통신 (이벤트 전송, 명령 수신 및 응답 처리)
│
├── utils/
│   ├── __init__.py
│   └── visualizer.py          # 디버그용 시각화 오버레이 (bbox, ID, FPS, Pose 키포인트 표시, 설정으로 ON/OFF)
│
├── models/
│   ├── yolov11seg-m.pt        # YOLOv11seg-m 모델 파일
│   └── yolov8n-pose.pt        # YOLOv8-pose 모델 파일
│   └── aruco_marker_model.pt  # (선택 사항) 마커 감지용 모델 파일
│
├── main.py                    # 프로젝트의 메인 실행 파일 및 전체 오케스트레이션
└── requirements.txt           # Python 패키지 의존성 목록

'''