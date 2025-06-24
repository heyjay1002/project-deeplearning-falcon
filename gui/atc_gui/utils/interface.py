from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
from dataclasses import dataclass
from enum import Enum
from config.constants import EventType, ObjectType, BirdRiskLevel, RunwayRiskLevel, Airportarea, MessagePrefix, Constants
from utils.logger import logger

class ConnectionState(Enum):
    """연결 상태 열거형"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class DetectedObject:
    """감지된 객체 정보를 저장하는 데이터 클래스"""    
    object_id: int
    object_type: ObjectType
    x_coord: float
    y_coord: float
    area: Airportarea
    event_type: Optional[EventType] = None
    timestamp: Optional[datetime] = None
    state_info: Optional[int] = None
    image_data: Optional[bytes] = None

    @property
    def position(self) -> tuple[float, float]:
        """객체의 위치 좌표 반환"""
        return (self.x_coord, self.y_coord)

    @property
    def is_bird(self) -> bool:
        """조류 객체 여부 확인"""
        return self.object_type == ObjectType.BIRD

    @property
    def is_fod(self) -> bool:
        """FOD 객체 여부 확인"""
        return self.object_type == ObjectType.FOD

    @property
    def is_person(self) -> bool:
        """사람 객체 여부 확인"""
        return self.object_type == ObjectType.PERSON

    @property
    def is_animal(self) -> bool:
        """동물 객체 여부 확인"""
        return self.object_type == ObjectType.ANIMAL

    @property
    def is_airplane(self) -> bool:
        """비행기 객체 여부 확인"""
        return self.object_type == ObjectType.AIRPLANE

    @property
    def is_vehicle(self) -> bool:
        """차량 객체 여부 확인"""
        return self.object_type == ObjectType.VEHICLE

    @property
    def is_work_person(self) -> bool:
        """작업자 객체 여부 확인"""
        return self.object_type == ObjectType.WORK_PERSON

    @property
    def is_work_vehicle(self) -> bool:
        """작업차량 객체 여부 확인"""
        return self.object_type == ObjectType.WORK_VEHICLE

    @property
    def image_base64(self) -> Optional[str]:
        """이미지 데이터를 Base64 문자열로 반환"""
        if self.image_data:
            return base64.b64encode(self.image_data).decode('utf-8')
        return None

    def to_dict(self) -> Dict[str, Any]:
        """객체 정보를 딕셔너리로 변환"""
        return {
            'event_type': self.event_type.value if self.event_type else None,
            'object_id': self.object_id,
            'object_type': self.object_type.value,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'area': self.area.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'state_info': self.state_info,
            'image_data': self.image_base64
        }

@dataclass
class BirdRisk:
    """조류 위험도 정보"""
    bird_risk_level: BirdRiskLevel
    
    def __post_init__(self):
        if not isinstance(self.bird_risk_level, BirdRiskLevel):
            raise ValueError(f"bird_risk_level은 BirdRiskLevel enum이어야 합니다: {self.bird_risk_level}")

    def to_dict(self) -> dict:
        return {"bird_risk_level": self.bird_risk_level.value}

@dataclass
class RunwayRisk:
    """활주로 위험도 정보"""
    runway_id: str  # 활주로 ID (A 또는 B)
    runway_risk_level: RunwayRiskLevel
    
    def __post_init__(self):
        if not isinstance(self.runway_risk_level, RunwayRiskLevel):
            raise ValueError(f"runway_risk_level은 RunwayRiskLevel enum이어야 합니다: {self.runway_risk_level}")
        if self.runway_id not in ['A', 'B']:
            raise ValueError(f"유효하지 않은 활주로 ID: {self.runway_id}")

    @property
    def enum(self) -> RunwayRiskLevel:        
        return self.runway_risk_level

    def to_dict(self) -> dict:
        return {
            'runway_id': self.runway_id,
            'runway_risk_level': self.runway_risk_level.value
        }

class MessageParser:
    """메시지 파싱 전용 클래스"""
    
    @staticmethod
    def parse_object_detail_info(data: str, image_data: bytes) -> DetectedObject:
        """MR_OD:OK,event_type,object_id,object_type,area,timestamp,image_size + 바이너리"""
        prefix = f"{MessagePrefix.MR_OD.value}:OK,"
        if not data.startswith(prefix):
            raise ValueError(f"잘못된 메시지 형식: {data}")
        
        data_body = data[len(prefix):]
        # image_size까지 분리 (이미지 데이터는 별도 전달)
        fields = data_body.split(',', 5)  # 6개 필드: event_type,object_id,object_type,area,timestamp,image_size
        
        if len(fields) < 6:
            logger.error(f"MR_OD: 필드 수 부족: {fields}")
            raise ValueError(f"필드 수 오류: {len(fields)} != 6")
        
        event_type = MessageParser._parse_event_type(fields[0])
        object_id = int(fields[1])
        obj_type = MessageParser._parse_object_type(fields[2])
        area = MessageParser._parse_area(fields[3])
        timestamp = MessageParser._parse_timestamp(fields[4])
        image_size = int(fields[5])
        
        # 이미지 크기 검증
        if len(image_data) != image_size:
            logger.warning(f"이미지 크기 불일치: {len(image_data)} != {image_size}")
        
        return DetectedObject(
            object_id=object_id,
            object_type=obj_type,
            x_coord=0.0,
            y_coord=0.0,
            area=area,
            event_type=event_type,
            timestamp=timestamp,
            image_data=image_data
        )
    
    @staticmethod
    def _parse_event_type(event_type_str: str) -> EventType:
        """이벤트 타입 파싱 - Constants 매핑 활용"""
        try:
            # 정수인 경우 매핑 테이블 사용
            event_type_id = int(event_type_str)
            if event_type_id in Constants.EVENT_TYPE_MAPPING:
                return Constants.EVENT_TYPE_MAPPING[event_type_id]
            else:
                raise ValueError(f"알 수 없는 이벤트 타입 ID: {event_type_id}")
        except ValueError:
            # 문자열인 경우 enum 이름으로 시도
            try:
                return EventType[event_type_str.upper()]
            except KeyError:
                # enum value로 시도
                for event_type in EventType:
                    if event_type.value == event_type_str:
                        return event_type
                raise ValueError(f"알 수 없는 이벤트 타입: {event_type_str}")
    
    @staticmethod
    def _parse_object_type(obj_type_str: str) -> ObjectType:
        """객체 타입 파싱 - Constants 매핑 활용"""
        try:
            # 정수인 경우 매핑 테이블 사용
            obj_type_id = int(obj_type_str)
            if obj_type_id in Constants.OBJECT_CLASS_MAPPING:
                return Constants.OBJECT_CLASS_MAPPING[obj_type_id]
            else:
                raise ValueError(f"알 수 없는 객체 타입 ID: {obj_type_id}")
        except ValueError:
            # 문자열인 경우
            obj_type_str_lower = obj_type_str.lower()
            
            # ObjectType enum value와 매칭
            for obj_type in ObjectType:
                if obj_type.value.lower() == obj_type_str_lower:
                    return obj_type
            
            # enum 이름으로 시도
            try:
                return ObjectType[obj_type_str.upper()]
            except KeyError:
                raise ValueError(f"객체 타입 오류: {obj_type_str}")
    
    @staticmethod
    def _parse_area(area_str: str) -> Airportarea:
        """구역 파싱 - Constants 매핑 활용"""
        try:
            # 정수인 경우 매핑 테이블 사용
            area_id = int(area_str)
            if area_id in Constants.area_MAPPING:
                return Constants.area_MAPPING[area_id]
            else:
                raise ValueError(f"알 수 없는 구역 ID: {area_id}")
        except ValueError:
            # 문자열인 경우
            try:
                return Airportarea[area_str.upper()]
            except KeyError:
                # enum value로 시도
                for area_type in Airportarea:
                    if area_type.value == area_str:
                        return area_type
                raise ValueError(f"구역 이름 오류: {area_str}")
    
    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """타임스탬프 파싱"""
        try:
            # ISO 8601 형식 처리
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Unix timestamp 처리
                return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, OSError) as e:
            raise ValueError(f"타임스탬프 형식 오류: {timestamp_str}") from e

class MessageInterface:
    """TCP 메시지 인터페이스 클래스"""
    
    @staticmethod
    def validate_bird_risk_level(risk_level: int) -> bool:
        """조류 위험도 값 유효성 검증"""
        return risk_level in Constants.BIRD_RISK_MAPPING
    
    @staticmethod
    def validate_runway_risk_level(risk_level: int) -> bool:
        """활주로 위험도 값 유효성 검증"""
        return risk_level in Constants.RUNWAY_RISK_MAPPING

    @staticmethod
    def parse_message(message: str) -> tuple[MessagePrefix, str]:
        """메시지 파싱"""
        if not message or Constants.Protocol.MESSAGE_SEPARATOR not in message:
            raise Exception(f"메시지 포맷 오류: {message}")
            
        parts = message.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
        if len(parts) != 2:
            raise Exception(f"메시지 포맷 오류: {message}")    
        
        prefix_str, data = parts
        try:
            prefix = MessagePrefix(prefix_str)
        except ValueError:
            raise Exception(f"알 수 없는 메시지 프리픽스: {prefix_str}")
        
        return prefix, data
    
    @staticmethod
    def parse_object_detail_info(object_str: str, image_data: bytes = b'') -> DetectedObject:
        """객체 정보 문자열 파싱 (호환성 유지)"""
        return MessageParser.parse_object_detail_info(object_str, image_data)
    
    @staticmethod
    def parse_object_detection_event(payload: str) -> List[DetectedObject]:
        """객체 감지 이벤트 파싱 - 여러 객체 지원 (ME_OD 형식)"""
        objects = []
        
        logger.debug(f"객체 감지 이벤트 파싱 시작: {payload[:200]}...")
        
        # 여러 객체가 ;로 구분된 경우 처리
        object_records = payload.split(Constants.Protocol.OBJECT_RECORD_SEPARATOR)
        logger.debug(f"분리된 객체 레코드 수: {len(object_records)}")
        
        for i, record in enumerate(object_records):
            if not record.strip():
                logger.debug(f"빈 레코드 건너뜀: 인덱스 {i}")
                continue
                
            logger.debug(f"객체 레코드 {i+1} 처리: {record}")
            
            try:
                parts = record.split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
                if len(parts) < 5:  # 최소 필수 필드 확인 (5개: object_id,object_type,x_coord,y_coord,area)
                    logger.warning(f"필수 필드 부족: {len(parts)} < 5")
                    continue
                
                # ME_OD 형식: object_id,object_type,x_coord,y_coord,area[,timestamp][,state_info]
                object_id = int(parts[0])
                object_type = MessageParser._parse_object_type(parts[1])
                x_coord = float(parts[2])
                y_coord = float(parts[3])
                area = MessageParser._parse_area(parts[4])
                
                # 타임스탬프 처리 (선택적)
                timestamp = None
                if len(parts) > 5 and parts[5].strip():
                    try:
                        timestamp = MessageParser._parse_timestamp(parts[5])
                    except Exception as e:
                        logger.debug(f"타임스탬프 파싱 실패: {e}, 현재 시간 사용")
                        timestamp = datetime.now()
                else:
                    # 타임스탬프가 없으면 현재 시간 사용
                    timestamp = datetime.now()
                
                # 선택적 필드들
                state_info = None
                image_data = None
                
                # 상태 정보 처리 (선택적)
                if len(parts) > 6 and parts[6].strip():
                    try:
                        state_info = int(parts[6].strip())
                    except ValueError:
                        logger.debug(f"상태 정보 파싱 실패: {parts[6]}")
                
                # 이미지 데이터 처리 (선택적)
                if len(parts) > 7 and parts[7].strip():
                    try:
                        image_b64 = parts[7].strip()
                        # Base64 패딩 추가
                        missing_padding = len(image_b64) % 4
                        if missing_padding:
                            image_b64 += '=' * (4 - missing_padding)
                        image_data = base64.b64decode(image_b64)
                    except Exception as e:
                        logger.debug(f"이미지 데이터 파싱 실패: {e}")
                
                # DetectedObject 생성 (ME_OD에는 event_type이 없으므로 기본값 사용)
                obj = DetectedObject(
                    object_id=object_id,
                    object_type=object_type,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    area=area,
                    event_type=EventType.HAZARD,  # 기본값
                    timestamp=timestamp,
                    state_info=state_info,
                    image_data=image_data
                )
                objects.append(obj)
                logger.debug(f"객체 {i+1} 생성 완료: ID {object_id}")
                
            except Exception as e:
                logger.error(f"객체 레코드 {i+1} 파싱 실패: {e}, 레코드: {record}")
                continue
        
        return objects
    
    @staticmethod
    def parse_first_detection_event(payload: str) -> List[DetectedObject]:
        """최초 객체 감지 이벤트 파싱 - 여러 객체 지원 (ME_FD 형식)"""
        objects = []
        
        logger.debug(f"최초 객체 감지 이벤트 파싱 시작: {payload[:200]}...")
        
        # 여러 객체가 ;로 구분된 경우 처리
        object_records = payload.split(Constants.Protocol.OBJECT_RECORD_SEPARATOR)
        logger.debug(f"분리된 객체 레코드 수: {len(object_records)}")
        
        for i, record in enumerate(object_records):
            if not record.strip():
                logger.debug(f"빈 레코드 건너뜀: 인덱스 {i}")
                continue
                
            logger.debug(f"객체 레코드 {i+1} 처리: {record}")
            
            try:
                parts = record.split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
                if len(parts) < 8:  # ME_FD는 최소 8개 필드 필요
                    logger.warning(f"필수 필드 부족: {len(parts)} < 8")
                    continue
                
                # ME_FD 형식: event_type,object_id,object_type,x_coord,y_coord,area,timestamp,image_size[,image_data[,state_info]]
                event_type = MessageParser._parse_event_type(parts[0])
                object_id = int(parts[1])
                object_type = MessageParser._parse_object_type(parts[2])
                x_coord = float(parts[3])
                y_coord = float(parts[4])
                area = MessageParser._parse_area(parts[5])
                timestamp = MessageParser._parse_timestamp(parts[6]) if parts[6].strip() else None
                image_size = int(parts[7])
                
                # 선택적 필드들
                image_data = None
                state_info = None
                
                # 이미지 데이터 처리 (선택적)
                if len(parts) > 8 and parts[8].strip():
                    try:
                        if len(parts[8]) == image_size:
                            # 바이너리 데이터인 경우
                            image_data = parts[8].encode('latin-1')
                        else:
                            # Base64 데이터인 경우
                            image_b64 = parts[8].strip()
                            missing_padding = len(image_b64) % 4
                            if missing_padding:
                                image_b64 += '=' * (4 - missing_padding)
                            image_data = base64.b64decode(image_b64)
                    except Exception as e:
                        logger.debug(f"이미지 데이터 파싱 실패: {e}")
                
                # 상태 정보 처리 (선택적)
                if len(parts) > 9 and parts[9].strip():
                    try:
                        state_info = int(parts[9].strip())
                    except ValueError:
                        logger.debug(f"상태 정보 파싱 실패: {parts[9]}")
                
                # DetectedObject 생성
                obj = DetectedObject(
                    object_id=object_id,
                    object_type=object_type,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    area=area,
                    event_type=event_type,
                    timestamp=timestamp,
                    state_info=state_info,
                    image_data=image_data
                )
                objects.append(obj)
                logger.debug(f"객체 {i+1} 생성 완료: ID {object_id}")
                
            except Exception as e:
                logger.error(f"객체 레코드 {i+1} 파싱 실패: {e}, 레코드: {record}")
                continue
        
        return objects
    
    @staticmethod
    def parse_bird_risk_level_event(data: str) -> BirdRiskLevel:
        """조류 위험도 변경 이벤트 메시지 파싱"""
        try:
            risk_level = int(data.strip())
        except ValueError:
            raise Exception(f"조류 위험도 값 오류: {data}")
            
        if not MessageInterface.validate_bird_risk_level(risk_level):
            raise Exception(f"조류 위험도 값 오류: {risk_level}")
            
        return Constants.BIRD_RISK_MAPPING[risk_level]
    
    @staticmethod
    def parse_runway_risk_level_event(data: str) -> RunwayRiskLevel:
        """활주로 위험도 변경 이벤트 메시지 파싱"""
        try:
            risk_level = int(data.strip())
        except ValueError:
            raise Exception(f"활주로 위험도 값 오류: {data}")
            
        if not MessageInterface.validate_runway_risk_level(risk_level):
            raise Exception(f"활주로 위험도 값 오류: {risk_level}")
            
        return Constants.RUNWAY_RISK_MAPPING[risk_level]
    
    @staticmethod
    def create_message(prefix: MessagePrefix, **kwargs) -> str:
        """메시지 생성 - Constants.Protocol.MESSAGE_FORMAT 활용"""
        try:
            format_str = Constants.Protocol.MESSAGE_FORMAT[prefix]
            
            # prefix 값을 kwargs에 추가
            kwargs['prefix'] = prefix.value
            
            # 형식 문자열에서 실제 사용할 필드만 추출
            import re
            field_pattern = r'\{(\w+)\}'
            required_fields = re.findall(field_pattern, format_str)
            
            # 필수 필드 검증
            for field in required_fields:
                if field not in kwargs and field != 'prefix':
                    raise ValueError(f"필수 필드 누락: {field}")
            
            # 메시지 생성
            message = format_str.format(**kwargs)
            
            # 선택적 필드 제거 (빈 대괄호 제거)
            message = re.sub(r'\[[^\]]*\]', '', message)
            message = re.sub(r'\*', '', message)  # 반복 표시 제거
            
            return message
            
        except KeyError as e:
            raise Exception(f"알 수 없는 메시지 프리픽스: {prefix}") from e
        except Exception as e:
            raise Exception(f"메시지 생성 실패: {e}") from e

    @staticmethod
    def create_object_detail_request(object_id: int) -> str:
        """객체 상세보기 요청 메시지 생성"""
        if not isinstance(object_id, int) or object_id < 0:
            raise ValueError("Invalid object ID")
        return MessageInterface.create_message(MessagePrefix.MC_OD, object_id=object_id)
    
    @staticmethod
    def create_cctv_request(camera_id: str) -> str:
        """CCTV 영상 요청 메시지 생성"""
        if camera_id not in ["A", "B"]:
            raise ValueError("Invalid CCTV ID")
        
        prefix = MessagePrefix.MC_CA if camera_id == "A" else MessagePrefix.MC_CB
        return MessageInterface.create_message(prefix)
    
    @staticmethod
    def create_map_request() -> str:
        """지도 영상 요청 메시지 생성"""
        return MessageInterface.create_message(MessagePrefix.MC_MP)

class ErrorHandler:
    """통합 에러 핸들러"""
    
    @staticmethod
    def handle_network_error(error: Exception, context: str) -> None:
        """네트워크 에러 처리"""
        if isinstance(error, Exception):
            logger.error(f"연결 오류 [{context}]: {error}")
        else:
            logger.error(f"알 수 없는 오류 [{context}]: {error}")

class ConnectionManager:
    """연결 상태 통합 관리"""
    
    def __init__(self):
        self.tcp_state = ConnectionState.DISCONNECTED
        self.udp_state = ConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    def set_tcp_state(self, state: ConnectionState):
        """TCP 연결 상태 설정"""
        self.tcp_state = state
        
    def set_udp_state(self, state: ConnectionState):
        """UDP 연결 상태 설정"""
        self.udp_state = state
        
    def get_overall_status(self) -> Dict[str, Any]:
        """전체 연결 상태 반환"""
        return {
            'tcp': self.tcp_state.value,
            'udp': self.udp_state.value,
            'reconnect_attempts': self.reconnect_attempts
        }
       
    def reset_reconnect_attempts(self):
        """재연결 시도 횟수 리셋"""
        self.reconnect_attempts = 0
    
    def increment_reconnect_attempts(self) -> bool:
        """재연결 시도 횟수 증가, 최대 시도 횟수 초과 여부 반환"""
        self.reconnect_attempts += 1
        return self.reconnect_attempts >= self.max_reconnect_attempts