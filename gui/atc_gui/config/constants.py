from enum import Enum

class EventType(Enum):
    """이벤트 타입"""
    HAZARD = "위험요소 감지"
    UNAUTH = "출입 위반"
    RESCUE = "구조"

class ObjectType(Enum):
    """지상 위험 요소 타입"""
    BIRD = "조류"
    FOD = "FOD"
    PERSON = "인간"
    ANIMAL = "동물"
    AIRPLANE = "비행기"
    VEHICLE = "차량"
    WORK_PERSON = "작업자"
    WORK_VEHICLE = "작업차량"
    UNKNOWN = "알 수 없음"

class BirdRiskLevel(Enum):
    """조류 위험도 등급"""
    LOW = "안전"
    MEDIUM = "주의"
    HIGH = "경고"

class RunwayRiskLevel(Enum):
    """활주로 위험도 등급"""
    LOW = "안전"
    HIGH = "경고"

class Airportarea(Enum):
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
    ME_FD = "ME_FD"      # 최초 객체 감지 이벤트
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
    
    # --- 매핑 테이블 ---
    EVENT_TYPE_MAPPING = {
        0: EventType.HAZARD,
        1: EventType.UNAUTH,
        2: EventType.RESCUE
    }

    OBJECT_CLASS_MAPPING = {
        0: ObjectType.BIRD,
        1: ObjectType.FOD,
        2: ObjectType.PERSON,
        3: ObjectType.ANIMAL,
        4: ObjectType.AIRPLANE,
        5: ObjectType.VEHICLE,
        6: ObjectType.WORK_PERSON,
        7: ObjectType.WORK_VEHICLE,
        8: ObjectType.UNKNOWN
    }
    
    BIRD_RISK_MAPPING = {
        0: BirdRiskLevel.LOW,
        1: BirdRiskLevel.MEDIUM,
        2: BirdRiskLevel.HIGH
    }
    
    RUNWAY_RISK_MAPPING = {
        0: RunwayRiskLevel.LOW,
        1: RunwayRiskLevel.HIGH
    }
    
    area_MAPPING = {    
        1: Airportarea.TWY_A,
        2: Airportarea.TWY_B,
        3: Airportarea.TWY_C,
        4: Airportarea.TWY_D,
        5: Airportarea.RWY_A,
        6: Airportarea.RWY_B,
        7: Airportarea.GRASS_A,
        8: Airportarea.GRASS_B,
        9: Airportarea.RAMP
    }
    
    SECURITY_LEVEL_MAPPING = {
        0: SecurityLevel.LEVEL_1,
        1: SecurityLevel.LEVEL_2,
        2: SecurityLevel.LEVEL_3,
    }

    # --- 통신 프로토콜 관련 ---
    class Protocol:
        """메시지 형식 및 구분자 관련 상수"""
        
        # 구분자
        MESSAGE_SEPARATOR = ":"
        OBJECT_FIELD_SEPARATOR = ","
        OBJECT_RECORD_SEPARATOR = ";"
        UDP_DATA_SEPARATOR = ":"
        
        # 메시지 형식 정의
        MESSAGE_FORMAT = {
            # 이벤트 메시지 (서버 -> GUI)
            MessagePrefix.ME_OD: "{prefix}:{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp}[,{state_info}][;{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp}[,{state_info}]]*",
            MessagePrefix.ME_FD: "{prefix}:{event_type},{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp},{image_size},{image_data}[;{event_type},{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp}[,{state_info}]]*",
            MessagePrefix.ME_BR: "{prefix}:{risk_level}",
            MessagePrefix.ME_RA: "{prefix}:{risk_level}",
            MessagePrefix.ME_RB: "{prefix}:{risk_level}",
            
            # 명령 메시지 (GUI -> 서버)
            MessagePrefix.MC_CA: "{prefix}",
            MessagePrefix.MC_CB: "{prefix}",
            MessagePrefix.MC_MP: "{prefix}",
            MessagePrefix.MC_OD: "{prefix}:{object_id}",
            
            # 응답 메시지 (서버 -> GUI)
            MessagePrefix.MR_CA: "{prefix}:{response}",
            MessagePrefix.MR_CB: "{prefix}:{response}",
            MessagePrefix.MR_MP: "{prefix}:{response}",
            MessagePrefix.MR_OD: "{prefix}:{response},{event_type},{object_id},{object_type},{area},{timestamp},{image_size},{image_data}"
        }