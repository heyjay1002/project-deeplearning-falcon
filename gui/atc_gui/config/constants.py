from enum import Enum

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

class BirdRiskLevel(Enum):
    """조류 위험도 등급"""
    LOW = "안전"
    MEDIUM = "주의"
    HIGH = "경고"

class RunwayRiskLevel(Enum):
    """활주로 위험도 등급"""
    LOW = "안전"
    MEDIUM = "주의"
    HIGH = "경고"

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
        0: ObjectType.BIRD,
        1: ObjectType.FOD,
        2: ObjectType.PERSON,
        3: ObjectType.ANIMAL,
        4: ObjectType.AIRPLANE,
        5: ObjectType.FIRE,
        6: ObjectType.VEHICLE,
        7: ObjectType.FALLEN_PERSON
    }
    
    BIRD_RISK_MAPPING = {
        0: BirdRiskLevel.LOW,
        1: BirdRiskLevel.MEDIUM,
        2: BirdRiskLevel.HIGH
    }
    
    RUNWAY_RISK_MAPPING = {
        0: RunwayRiskLevel.LOW,
        1: RunwayRiskLevel.MEDIUM,
        2: RunwayRiskLevel.HIGH
    }
    
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
    
    SECURITY_LEVEL_MAPPING = {
        0: SecurityLevel.LEVEL_1,
        1: SecurityLevel.LEVEL_2,
        2: SecurityLevel.LEVEL_3,
    }
    
    # 위험도별 색상
    RISK_COLORS = {
        BirdRiskLevel.LOW: "#00FF00",      # 녹색
        BirdRiskLevel.MEDIUM: "#FFFF00",   # 노란색
        BirdRiskLevel.HIGH: "#FF0000",     # 빨간색
        RunwayRiskLevel.LOW: "#00FF00",    # 녹색
        RunwayRiskLevel.MEDIUM: "#FFFF00", # 노란색
        RunwayRiskLevel.HIGH: "#FF0000"    # 빨간색
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
    
    # 객체 정보 형식
    OBJECT_INFO = "{object_id},{object_type},{x_coord},{y_coord},{zone},{timestamp}[,{extra_info}]"
    OBJECT_INFO_DETAIL = "{object_id},{object_type},{x_coord},{y_coord},{zone},{timestamp},{image_data}" 