from enum import Enum

class ObjectType(Enum):
    """지상 위험 요소 타입"""
    UNKNOWN = "알 수 없음"
    BIRD = "조류"
    DRONE = "드론"
    AIRCRAFT = "항공기"
    VEHICLE = "차량"
    PERSON = "사람"
    FOD = "FOD"
    ANIMAL = "동물"
    AIRPLANE = "비행기"
    FIRE = "화재"
    FALLEN_PERSON = "쓰러짐"

class BirdRiskLevel(Enum):
    """조류 위험도 등급"""
    NONE = "없음"
    LOW = "안전"
    MEDIUM = "주의"
    HIGH = "경고"
    CRITICAL = "긴급"

class AirportZone(Enum):
    """공항 구역 식별자"""    
    UNKNOWN = "알 수 없음"
    RUNWAY_A = "활주로 A"
    RUNWAY_B = "활주로 B"
    TAXIWAY = "택시로"
    APRON = "부지"
    TERMINAL = "터미널"
    PARKING = "주차장"
    MAINTENANCE = "보수"
    CARGO = "화물"
    PERIMETER = " province"
    GRASS_A = "GRASS_A"
    GRASS_B = "GRASS_B"
    RAMP = "RAMP"

class SecurityLevel(Enum):
    """보안 등급"""
    LEVEL_1 = "무제한"
    LEVEL_2 = "제한"
    LEVEL_3 = "금지"

class AccessTarget(Enum):
    """출입 대상"""
    VEHICLE = "차량"
    PERSON = "인원"

class CameraID(Enum):
    """CCTV 카메라 식별자"""
    A = "A"
    B = "B"

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

class Constants:
    """상수 정의 클래스"""
    
    # 매핑 테이블
    OBJECT_CLASS_MAPPING = {
        0: ObjectType.UNKNOWN,
        1: ObjectType.BIRD,
        2: ObjectType.DRONE,
        3: ObjectType.AIRCRAFT,
        4: ObjectType.VEHICLE,
        5: ObjectType.PERSON
    }
    
    BIRD_RISK_MAPPING = {
        0: BirdRiskLevel.NONE,
        1: BirdRiskLevel.LOW,
        2: BirdRiskLevel.MEDIUM,
        3: BirdRiskLevel.HIGH,
        4: BirdRiskLevel.CRITICAL
    }
    
    ZONE_MAPPING = {
        0: AirportZone.UNKNOWN,
        1: AirportZone.RUNWAY_A,
        2: AirportZone.RUNWAY_B,
        3: AirportZone.TAXIWAY,
        4: AirportZone.APRON,
        5: AirportZone.TERMINAL,
        6: AirportZone.PARKING,
        7: AirportZone.MAINTENANCE,
        8: AirportZone.CARGO,
        9: AirportZone.PERIMETER
    }
    
    SECURITY_LEVEL_MAPPING = {
        0: SecurityLevel.LEVEL_1,
        1: SecurityLevel.LEVEL_2,
        2: SecurityLevel.LEVEL_3,
    }
    
    # 위험도별 색상
    RISK_COLORS = {
        BirdRiskLevel.LOW: "#00FF00",      # 녹색
        BirdRiskLevel.MEDIUM: "#FFFF00",   # 노란색
        BirdRiskLevel.HIGH: "#FF0000"      # 빨간색
    }
    
    # 메시지 형식
    MESSAGE_FORMAT = {
        # 이벤트 메시지 (서버 -> GUI)
        MessagePrefix.ME_OD: "{prefix}:{object_info}[;{object_info}]*",  # 객체 감지 이벤트
        MessagePrefix.ME_BR: "{prefix}:{risk_level}",    # 조류 위험도 변경 이벤트
        MessagePrefix.ME_RA: "{prefix}:{risk_level}",    # 활주로 A 위험도 변경 이벤트
        MessagePrefix.ME_RB: "{prefix}:{risk_level}",    # 활주로 B 위험도 변경 이벤트
        
        # 명령 메시지 (GUI -> 서버)
        MessagePrefix.MC_CA: "{prefix}",              # CCTV A 영상 요청
        MessagePrefix.MC_CB: "{prefix}",              # CCTV B 영상 요청
        MessagePrefix.MC_MP: "{prefix}",              # 지도 영상 요청
        MessagePrefix.MC_OD: "{prefix}:{object_id}",  # 객체 상세보기 요청
        
        # 응답 메시지 (서버 -> GUI)
        MessagePrefix.MR_CA: "{prefix}:{response}",    # CCTV A 응답
        MessagePrefix.MR_CB: "{prefix}:{response}",    # CCTV B 응답
        MessagePrefix.MR_MP: "{prefix}:{response}",    # 지도 응답
        MessagePrefix.MR_OD: "{prefix}:{response}[,{object_info_detail}]"  # 객체 상세보기 응답
    }
    
    # 구분자
    MESSAGE_SEPARATOR = ":"            # 프리픽스와 데이터 구분자
    OBJECT_FIELD_SEPARATOR = ","        # 필드 구분
    OBJECT_RECORD_SEPARATOR = ";"       # 객체 간 구분
    UDP_DATA_SEPARATOR = ":"           # 카메라 ID와 바이너리 이미지 데이터 구분자
    
    # 프로토콜 상수
    UDP_HEADER_LENGTH = 2              # "A:" 또는 "B:" 형식의 헤더 길이
    
    # 객체 정보 형식
    OBJECT_INFO = "{object_id},{object_type},{x_coord},{y_coord},{zone},{timestamp}[,{extra_info}]"
    OBJECT_INFO_DETAIL = "{object_id},{object_type},{x_coord},{y_coord},{zone},{timestamp},{image_data}" 