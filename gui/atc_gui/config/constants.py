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
    PERSON = "일반인"
    ANIMAL = "동물"
    AIRPLANE = "비행기"
    VEHICLE = "일반차량"
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

class AirportArea(Enum):
    """공항 구역 식별자"""    
    TWY_A = "TWY_A"
    TWY_B = "TWY_B"
    TWY_C = "TWY_C"
    TWY_D = "TWY_D"
    RWY_A = "RWY_A"
    RWY_B = "RWY_B"
    GRASS_A = "GRASS_A"
    GRASS_B = "GRASS_B"

class SecurityLevel(Enum):
    """보안 등급"""
    OPEN = "출입 허가"
    AUTH_ONLY = "작업자 출입 허가"
    NO_ENTQ = "출입 불가"

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
    # 메인 페이지 이벤트 메시지 (서버 -> GUI)
    ME_OD = "ME_OD"      # 객체 감지 이벤트
    ME_FD = "ME_FD"      # 최초 객체 감지 이벤트
    ME_BR = "ME_BR"      # 조류 위험도 변경 이벤트
    ME_RA = "ME_RA"      # 활주로 A 위험도 변경 이벤트
    ME_RB = "ME_RB"      # 활주로 B 위험도 변경 이벤트
    
    # 메인 페이지 명령 메시지 (GUI -> 서버)
    MC_CA = "MC_CA"      # CCTV A 영상 요청
    MC_CB = "MC_CB"      # CCTV B 영상 요청
    MC_MP = "MC_MP"      # 지도 영상 요청
    MC_OD = "MC_OD"      # 객체 상세보기 요청
    
    # 메인 페이지 응답 메시지 (서버 -> GUI)
    MR_CA = "MR_CA"      # CCTV A 응답
    MR_CB = "MR_CB"      # CCTV B 응답
    MR_MP = "MR_MP"      # 지도 응답
    MR_OD = "MR_OD"      # 객체 상세보기 응답

    # 출입 페이지 명령/이벤트 메시지 (GUI -> 서버)
    AC_AC = "AC_AC"      # 구역별 출입 등급 요청
    AC_UA = "AC_UA"      # 구역별 출입 등급 업데이트 요청

    # 출입 페이지 응답 메시지 (서버 -> GUI)
    AR_AC = "AR_AC"      # 구역별 출입 등급 응답
    AR_UA = "AR_UA"      # 구역별 출입 등급 업데이트 응답

    # 로그 페이지 명령 메시지 (GUI -> 서버)
    LC_OL = "LC_OL"      # 객체 감지 이력 조회 요청
    LC_OI = "LC_OI"      # 객체 이미지 조회 요청
    LC_BL = "LC_BL"      # 조류 위험도 등급 변화 이력 조회 요청
    LC_RL = "LC_RL"      # 활주로 요청 응답 이력 조회 요청

    # 로그 페이지 응답 메시지 (서버 -> GUI)
    LR_OL = "LR_OL"      # 객체 감지 이력 응답
    LR_OI = "LR_OI"      # 객체 이미지 응답
    LR_BL = "LR_BL"      # 조류 위험도 등급 변화 이력 응답
    LR_RL = "LR_RL"      # 활주로 요청 응답 이력 응답

class Constants:
    """상수 정의 클래스"""
    
    # --- 매핑 테이블 ---
    EVENT_TYPE_MAPPING = {
        1: EventType.HAZARD,
        2: EventType.UNAUTH,
        3: EventType.RESCUE
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
    
    AREA_MAPPING = {    
        1: AirportArea.TWY_A,
        2: AirportArea.TWY_B,
        3: AirportArea.TWY_C,
        4: AirportArea.TWY_D,
        5: AirportArea.RWY_A,
        6: AirportArea.RWY_B,
        7: AirportArea.GRASS_A,
        8: AirportArea.GRASS_B
    }
    
    SECURITY_LEVEL_MAPPING = {
        1: SecurityLevel.OPEN,
        2: SecurityLevel.AUTH_ONLY,
        3: SecurityLevel.NO_ENTQ,
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
            MessagePrefix.ME_OD: "{prefix}:{object_id},{object_type},{x_coord},{y_coord},{area}[,{state_info}][;{object_id},{object_type},{x_coord},{y_coord},{area}[,{state_info}]]*",
            MessagePrefix.ME_FD: "{prefix}:{event_type},{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp}[,{state_info}],{image_size},{image_data}[;{event_type},{object_id},{object_type},{x_coord},{y_coord},{area},{timestamp}[,{state_info}],{image_size},{image_data}]*",
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
            MessagePrefix.MR_OD: "{prefix}:{response},{event_type},{object_id},{object_type},{area},{timestamp},{image_size},{image_data}",

            # 출입 페이지 명령/이벤트 메시지 (GUI -> 서버)
            MessagePrefix.AC_AC: "{prefix}",
            MessagePrefix.AC_UA: "{prefix}:{TWY_A_level},{TWY_B_level},{TWY_C_level},{TWY_D_level},{RWY_A_level},{RWY_B_level},{GRASS_A_level},{GRASS_B_level}",

            # 출입 페이지 응답 메시지 (서버 -> GUI)
            MessagePrefix.AR_AC: "{prefix}:{response},{TWY_A_level},{TWY_B_level},{TWY_C_level},{TWY_D_level},{RWY_A_level},{RWY_B_level},{GRASS_A_level},{GRASS_B_level}",
            MessagePrefix.AR_UA: "{prefix}:{response}",

            # 로그 페이지 명령 메시지 (GUI -> 서버)
            MessagePrefix.LC_OL: "{prefix}:{start_time},{end_time}",
            MessagePrefix.LC_OI: "{prefix}:{object_id}",
            MessagePrefix.LC_BL: "{prefix}:{start_time},{end_time}",
            MessagePrefix.LC_RL: "{prefix}:{start_time},{end_time}",

            # 로그 페이지 응답 메시지 (서버 -> GUI)
            MessagePrefix.LR_OL: "{prefix}:{response},{event_type},{object_id},{object_type},{area},{timestamp}[;{event_type},{object_id},{object_type},{area},{timestamp}]*",
            MessagePrefix.LR_OI: "{prefix}:{response},{image_size},{image_data}",
            MessagePrefix.LR_BL: "{prefix}:{response},{bird_risk_level},{timestamp}[;{bird_risk_level},{timestamp}]*",
            MessagePrefix.LR_RL: "{prefix}:{response},{request_type},{response_type},{timestamp},{timestamp}[;{request_type},{response_type},{timestamp},{timestamp}]*"
        }