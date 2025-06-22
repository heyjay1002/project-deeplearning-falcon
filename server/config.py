"""
시스템 전체 설정
"""

# 네트워크 설정
DEFAULT_HOST = "0.0.0.0"
DEFAULT_CLIENT_HOST = "127.0.0.1"

# TCP 설정
TCP_BUFFER_SIZE = 4096

TCP_PORT_IMAGE = 5000
TCP_PORT_ADMIN = 5100
TCP_PORT_BIRD = 5200
TCP_PORT_PILOT = 5300

# UDP 설정
UDP_BUFFER_SIZE = 131072

UDP_PORT_IDS_VIDEO = 4000  # IDS -> Main Server
UDP_PORT_ADMIN_VIDEO = 4100  # Main Server -> Admin PC

# 데이터베이스 설정
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "falcon_db"
DB_USER = "root"
DB_PASSWORD = "1234"

# 시스템 설정
MAX_QUEUE_SIZE = 100

# 비디오 설정
DEFAULT_FPS = 30
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480

# 버퍼 설정
VIDEO_FRAME_BUFFER = 30  # 2초 분량 (30fps 기준)

# 디버그 설정
AUTO_DELETE_DB_ON_START = True  # 서버 시작 시 DB의 탐지 이벤트 초기화 여부
DEBUG_OBJECT_ID_START = False  # True면 object_id를 1000부터 시작

# 프레임 크기 (실제 크기로 업데이트됨)
frame_width = None
frame_height = None

# 맵 크기 (좌표 변환용)
MAP_WIDTH = 960
MAP_HEIGHT = 720