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

class BirdRiskLevel(Enum):
    """조류 위험도 등급"""
    LOW = "안전"
    MEDIUM = "주의"
    HIGH = "경고"

BIRD_RISK_MAPPING = {
    0: BirdRiskLevel.LOW,
    1: BirdRiskLevel.MEDIUM,
    2: BirdRiskLevel.HIGH
}

# 위험도별 색상
RISK_COLORS = {
    BirdRiskLevel.LOW: "#00FF00",      # 녹색
    BirdRiskLevel.MEDIUM: "#FFFF00",   # 노란색
    BirdRiskLevel.HIGH: "#FF0000"      # 빨간색
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
    LEVEL_1 = "무제한"
    LEVEL_2 = "제한"
    LEVEL_3 = "금지"

class AccessTarget(Enum):
    """출입 대상"""
    VEHICLE = "차량"
    PERSON = "인원"

SECURITY_LEVEL_MAPPING = {
    0: SecurityLevel.LEVEL_1,
    1: SecurityLevel.LEVEL_2,
    2: SecurityLevel.LEVEL_3,
}

# ============================================================================
# UDP 프로토콜
# ============================================================================

# CCTV 카메라 ID
class CameraID(Enum):
    """CCTV 카메라 식별자"""
    A = "A"
    B = "B"

# UDP 데이터 형식
UDP_DATA_SEPARATOR = ":"  # 카메라 ID와 바이너리 이미지 데이터 구분자

# UDP 데이터 파싱 상수
UDP_HEADER_LENGTH = 2     # "A:" 또는 "B:" 형식의 헤더 길이

# ============================================================================
# TCP 메시지 프로토콜
# ============================================================================

class MessagePrefix(Enum):
    """메시지 프리픽스"""
    # 이벤트 메시지 (서버 -> GUI)
    ME_OD = "ME_OD"      # 객체 감지 이벤트
    ME_BR = "ME_BR"      # 조류 위험도 변경 이벤트
    ME_RA = "ME_RA"      # 활주로 A 위험도 변경 이벤트
    ME_RB = "ME_RB"      # 활주로 B 위험도 변경 이벤트
    
    # 명령 메시지 (GUI -> 서버)
    MC_CA = "MC_CA"      # CCTV A 영상 요청
    MC_CB = "MC_CB"      # CCTV B 영상 요청
    MC_MP = "MC_MP"      # 지도 영상 요청
    MC_OD = "MC_OD"      # 객체 상세보기 요청
    
    # 응답 메시지 (서버 -> GUI)
    MR_CA = "MR_CA"      # CCTV A 응답
    MR_CB = "MR_CB"      # CCTV B 응답
    MR_MP = "MR_MP"      # 지도 응답
    MR_OD = "MR_OD"      # 객체 상세보기 응답

# 객체 정보 필드 정의
OBJECT_INFO = "{object_id},{class},{x_coord},{y_coord},{zone},{timestamp}[,{extra_info}]"  # 기본 객체 정보
OBJECT_INFO_DETAIL = "{object_id},{class},{x_coord},{y_coord},{zone},{timestamp},{image_data}"  # 상세 객체 정보 (이미지 포함)

# 메시지 형식 정의
# 서버 -> GUI (이벤트/응답): 프리픽스:데이터
# GUI -> 서버 (명령): 프리픽스만
MESSAGE_FORMAT = {
    # 이벤트 메시지 (서버 -> GUI)
    MessagePrefix.ME_OD: (
        f"ME_OD:{OBJECT_INFO}"  # 첫 번째 객체 정보
        f"[;{OBJECT_INFO}]*"    # 추가 객체 정보가 있는 경우, 세미콜론으로 구분
    ),  # 객체 감지 이벤트
    
    MessagePrefix.ME_BR: "ME_BR:{risk_level}",    # 조류 위험도 변경 이벤트
    MessagePrefix.ME_RA: "ME_RA:{risk_level}",    # 활주로 A 위험도 변경 이벤트
    MessagePrefix.ME_RB: "ME_RB:{risk_level}",    # 활주로 B 위험도 변경 이벤트
    
    # 명령 메시지 (GUI -> 서버)
    MessagePrefix.MC_CA: "MC_CA",              # CCTV A 영상 요청
    MessagePrefix.MC_CB: "MC_CB",              # CCTV B 영상 요청
    MessagePrefix.MC_MP: "MC_MP",              # 지도 영상 요청
    MessagePrefix.MC_OD: "MC_OD:{object_id}",  # 객체 상세보기 요청
    
    # 응답 메시지 (서버 -> GUI)
    MessagePrefix.MR_CA: "MR_CA:{response}",    # CCTV A 응답
    MessagePrefix.MR_CB: "MR_CB:{response}",    # CCTV B 응답
    MessagePrefix.MR_MP: "MR_MP:{response}",    # 지도 응답
    MessagePrefix.MR_OD: (
        f"MR_OD:{{response}}"  # 기본 응답 (ERR인 경우 여기까지)
        f"[,{OBJECT_INFO_DETAIL}]"  # OK인 경우에만 객체 상세 정보 포함
    )  # 객체 상세보기 응답
}

# 메시지 파싱을 위한 상수
MESSAGE_SEPARATOR = ":"            # 프리픽스와 데이터 구분자

# 객체 정보 파싱을 위한 상수
OBJECT_FIELD_SEPARATOR = ","        # 필드 구분
OBJECT_RECORD_SEPARATOR = ";"       # 객체 간 구분

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