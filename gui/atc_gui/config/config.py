from enum import Enum, IntEnum

# ============================================================================
# 서버 연결 설정
# ============================================================================

# TCP 서버 연결 정보 (객체 감지 데이터 수신)
TCP_SERVER_IP = "127.0.0.1"
TCP_SERVER_PORT = 8080

# UDP 서버 연결 정보 (CCTV 영상 데이터 수신)
UDP_SERVER_IP = "127.0.0.1"
UDP_SERVER_PORT = 8081

# 연결 설정
CONNECTION_TIMEOUT = 5
RECONNECT_INTERVAL = 3
TCP_BUFFER_SIZE = 4096
UDP_BUFFER_SIZE = 65536

# ============================================================================
# 지상 위험 요소 타입
# ============================================================================

class ObjectType(Enum):
    """지상 위험 요소 타입"""
    BIRD = "조류"
    FOD = "FOD"
    PERSON = "사람"
    ANIMAL = "동물"
    AIRPLANE = "비행기"
    FIRE = "화재"
    VEHICLE = "차량"
    FALLEN_PERSON = "쓰러짐"
    # RESCUE_REQUEST = "구조요청"    

OBJECT_CLASS_MAPPING = {
    0: ObjectType.BIRD,
    1: ObjectType.FOD,
    2: ObjectType.PERSON,
    3: ObjectType.ANIMAL,
    4: ObjectType.AIRPLANE,
    5: ObjectType.FIRE,
    6: ObjectType.VEHICLE,
    7: ObjectType.FALLEN_PERSON,
    # 8: ObjectType.RESCUE_REQUEST
}

# ============================================================================
# 조류 위험도 등급
# ============================================================================

class BirdRiskLevel(IntEnum):
    """조류 위험도 등급"""
    LOW = 0        # 안전
    MEDIUM = 1     # 주의
    HIGH = 2       # 경고

BIRD_RISK_MAPPING = {
    0: BirdRiskLevel.LOW,
    1: BirdRiskLevel.MEDIUM,
    2: BirdRiskLevel.HIGH
}

# 위험도별 색상
RISK_COLORS = {
    BirdRiskLevel.LOW: "#00FF00",      # 녹색
    BirdRiskLevel.MEDIUM: "#FFFF00",   # 노란색
    BirdRiskLevel.HIGH: "#FF0000"    # 빨간색
}

# ============================================================================
# 공항 구역 정의
# ============================================================================

class AirportZone(Enum):
    """공항 구역 식별자"""    
    TWY_A = "TWY_A"
    TWY_B = "TWY_B"
    TWY_C = "TWY_C"
    TWY_D = "TWY_D"
    RWY_A = "RWY_A"
    RWY_B = "RWY_B"
    GRASS_A = "GRASS_A"
    GRASS_B = "GRASS_B"
    RAMP = "RAMP"

ZONE_MAPPING = {    
    1: AirportZone.TWY_A,
    2: AirportZone.TWY_B,
    3: AirportZone.TWY_C,
    4: AirportZone.TWY_D,
    5: AirportZone.RWY_A,
    6: AirportZone.RWY_B,
    7: AirportZone.GRASS_A,
    8: AirportZone.GRASS_B,
    9: AirportZone.RAMP
}

# ============================================================================
# 출입 조건 및 보안 등급
# ============================================================================

class SecurityLevel(Enum):
    """보안 등급"""
    LEVEL_1 = "UNRESTRICTED"
    LEVEL_2 = "RESTRICTED"
    LEVEL_3 = "FORBIDDEN"

class AccessTarget(Enum):
    """출입 대상"""
    VEHICLE = "차량"
    PERSONNEL = "인원"

SECURITY_LEVEL_MAPPING = {
    0: SecurityLevel.LEVEL_1,
    1: SecurityLevel.LEVEL_2,
    2: SecurityLevel.LEVEL_3,
}

# ============================================================================
# 알림 타입
# ============================================================================

class AlertType(Enum):
    """알림 타입"""
    GROUND_HAZARD = "지상_위험요소"
    BIRD_RISK = "조류_위험도"
    ACCESS_VIOLATION = "출입_위반"
    RESCUE_NEEDED = "구조_필요"
    # PILOT_REQUEST = "조종사_요청"



# ============================================================================
# UDP 프로토콜
# ============================================================================

# UDP 상수 추가

# ============================================================================
# TCP 메시지 프로토콜
# ============================================================================

class MessageType(Enum):
    """메시지 타입"""
    ME = "EVENT"        # 서버 -> GUI (이벤트 알림)
    MC = "COMMAND"      # GUI -> 서버 (요청/명령)
    MR = "RESPONSE"     # 서버 -> GUI (응답)

class MessageCategory(Enum):
    """메시지 카테고리"""
    OD = "OBJECT_DETECTION"
    BR = "BIRD_RISK_UPDATE"
    RA = "RWY_A_RISK"
    RB = "RWY_B_RISK"
    CA = "CCTV_A"
    CB = "CCTV_B"    
    MP = "MAP"      # CCTV 송출 멈추기 위한 목적

class MessagePrefix:
    """미리 정의된 메시지 프리픽스"""
    # 이벤트 (서버 -> GUI)
    OBJECT_DETECTION = "ME_OD"      # 객체 감지 이벤트
    BIRD_RISK_UPDATE = "ME_BR"      # 조류 위험도 업데이트
    RWY_A_RISK = "ME_RA"           # 활주로 A 위험도
    RWY_B_RISK = "ME_RB"   

# 메시지 파싱을 위한 상수
MESSAGE_SEPARATOR = ":"            # 프리픽스와 데이터 구분자
MESSAGE_PREFIX_LENGTH = 5          # "ME_OD" 같은 프리픽스 길이

class CCTVCommand(Enum):
    """CCTV 제어 커맨드"""
    CCTV_A = "MC_CA"      # CCTV A 영상 요청
    CCTV_B = "MC_CB"      # CCTV B 영상 요청
    MAP = "MC_MP"         # MAP 영상 요청(CCTV A,B 영상 중지를 위한 것임)

class CCTVResponse(Enum):
    """CCTV 응답 코드"""
    OK = "OK"               # 성공
    ERR = "ERROR"           # 실패

# CCTV 커맨드별 응답 형식
CCTV_RESPONSE_FORMAT = {
    CCTVCommand.CCTV_A: "MC_CA:{response}",
    CCTVCommand.CCTV_B: "MC_CB:{response}",
    CCTVCommand.MAP: "MC_MP:{response}"
}

# # CCTV 인덱스 매핑
# CCTV_INDEX_MAP = {
#     0: CCTVMAPCommand.CCTV_A,
#     1: CCTVMAPCommand.CCTV_B
# }

# ============================================================================
# 객체 감지 데이터 프로토콜
# ============================================================================

class ObjectDetectionCommand(Enum):
    """객체 감지 커맨드"""
    DETECTION_EVENT = "ME_OD"

# 객체 감지 데이터 필드 정의
OBJECT_DETECTION_FIELDS = [
    'object_id',      # 1001
    'object_type',    # 1 or 'FOD'
    'x_coord',        # 100
    'y_coord',        # 100
    'zone',          # 'RWY_A'
    'timestamp',     # '2025-06-05T19:21:00Z'
    'extra_info'     # 'rescue' (선택적, 객체가 사람인 경우에만)
]

# 데이터 파싱 상수
OBJECT_DETECTION_SEPARATOR = ":"    # 커맨드와 데이터 구분
OBJECT_FIELD_SEPARATOR = ","        # 필드 구분
OBJECT_RECORD_SEPARATOR = ";"       # 객체 간 구분

# 필수 필드 개수
OBJECT_DETECTION_MIN_FIELDS = 6     # extra_info는 선택적
OBJECT_DETECTION_MAX_FIELDS = 7

# ============================================================================
# UI 설정 및 상수
# ============================================================================

# # 메인 윈도우
# WINDOW_TITLE = "FALCON - 딥러닝 기반 활주로 안전 대응 시스템"
# WINDOW_MIN_WIDTH = 1200
# WINDOW_MIN_HEIGHT = 800

# # 페이지 인덱스
# class PageIndex(IntEnum):
#     MAIN = 0
#     ACCESS = 1
#     LOG = 2

# # 스택 위젯 인덱스
# class StackIndex(IntEnum):
#     MAP = 0
#     CCTV_1 = 1
#     CCTV_2 = 2
#     CCTV_3 = 3

# class ObjectAreaIndex(IntEnum):
#     TABLE = 0
#     DETAIL = 1

# # 테이블 설정
# TABLE_ROW_HEIGHT = 30
# TABLE_HEADER_HEIGHT = 35
# MAX_TABLE_ROWS = 1000

# # 이미지 및 지도 설정
# MAP_WIDTH = 1000
# MAP_HEIGHT = 600
# MARKER_SIZE = 20
# IMAGE_REFRESH_INTERVAL = 33  # 약 30fps

# ============================================================================
# 알림 설정
# ============================================================================

ALERT_DURATION = 5  # 알림 지속 시간 (초)
ALERT_VOLUME = 0.8  # 알림음 볼륨 (0.0 ~ 1.0)

# ============================================================================
# 데이터 처리 설정
# ============================================================================

DATA_REFRESH_INTERVAL = 100  # 데이터 수신 주기 (밀리초)
MAX_DETECTED_OBJECTS = 100   # 최대 동시 감지 객체 수

# ============================================================================
# 로그 설정
# ============================================================================

LOG_FILE_PATH = "logs/falcon_system.log"
LOG_LEVEL = "INFO"
LOG_MAX_SIZE = 10        # MB
LOG_BACKUP_COUNT = 5
LOG_RETENTION_DAYS = 30  # 이력 보관 기간 (일)

# ============================================================================
# 개발/디버그 설정
# ============================================================================

DEBUG_MODE = True                # True: 샘플 데이터 사용
SAMPLE_DATA_INTERVAL = 2         # 샘플 데이터 생성 간격 (초)
NETWORK_DEBUG = True             # 네트워크 연결 로깅 활성화