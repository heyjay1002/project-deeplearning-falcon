from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import base64
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from config import ObjectType, BirdRiskLevel, RunwayRiskLevel, AirportZone, ExtraInfo, MessagePrefix, Constants
from utils.logger import logger


class ConnectionState(Enum):
    """연결 상태 열거형"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class NetworkException(Exception):
    """네트워크 관련 예외 기본 클래스"""
    pass


class ConnectionError(NetworkException):
    """연결 오류"""
    pass


class ParseError(NetworkException):
    """파싱 오류"""
    pass


class ProtocolError(NetworkException):
    """프로토콜 오류"""
    pass


@dataclass
class ProcessedFrame:
    """처리된 프레임 데이터"""
    frame: Any  # numpy array
    camera_id: str
    image_id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: Optional[float] = None

@dataclass
class DetectedObject:
    """개선된 감지 객체 정보를 저장하는 데이터 클래스"""
    object_id: int
    object_type: ObjectType
    x_coord: float
    y_coord: float
    zone: AirportZone
    timestamp: datetime
    extra_info: Optional[ExtraInfo] = None
    image_data: Optional[bytes] = None  # bytes로 통일
    
    def __post_init__(self):
        """데이터 유효성 검증"""
        self._validate_all_fields()
    
    def _validate_all_fields(self):
        """모든 필드 유효성 검증"""
        validators = [
            self._validate_object_id,
            self._validate_coordinates,
            self._validate_timestamp
        ]
        for validator in validators:
            validator()
    
    def _validate_object_id(self):
        """객체 ID 유효성 검증"""
        if not isinstance(self.object_id, int) or self.object_id < 0:
            raise ValueError(f"Invalid object ID: {self.object_id}")
    
    def _validate_coordinates(self):
        """좌표 유효성 검증"""
        if not isinstance(self.x_coord, (int, float)) or not isinstance(self.y_coord, (int, float)):
            raise ValueError(f"Invalid coordinates: ({self.x_coord}, {self.y_coord})")
    
    def _validate_timestamp(self):
        """타임스탬프 유효성 검증"""
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"Invalid timestamp: {self.timestamp}")
    
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
            'object_id': self.object_id,
            'object_type': self.object_type.value,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'zone': self.zone.value,
            'timestamp': self.timestamp.isoformat(),
            'extra_info': self.extra_info.value,
            'image_data': self.image_base64
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectedObject':
        """딕셔너리로부터 객체 생성"""
        image_data = None
        if data.get('image_data'):
            try:
                image_data = base64.b64decode(data['image_data'])
            except Exception as e:
                logger.error(f"이미지 데이터 디코딩 실패: {e}")
        
        return cls(
            object_id=data['object_id'],
            object_type=ObjectType(data['object_type']),
            x_coord=data['x_coord'],
            y_coord=data['y_coord'],
            zone=AirportZone(data['zone']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            extra_info=ExtraInfo(data['extra_info']),
            image_data=image_data,
        )

@dataclass
class BirdRisk:
    """조류 위험도 정보"""
    bird_risk_level: BirdRiskLevel  # enum 객체로 받음
    
    def __post_init__(self):
        if not isinstance(self.bird_risk_level, BirdRiskLevel):
            raise ValueError(f"bird_risk_level은 BirdRiskLevel enum이어야 합니다: {self.bird_risk_level}")

    def to_dict(self) -> dict:
        return {"bird_risk_level": self.bird_risk_level.value}

@dataclass
class RunwayRisk:
    """활주로 위험도 정보"""
    runway_id: str  # 활주로 ID (A 또는 B)
    runway_risk_level: RunwayRiskLevel  # enum 객체로 받음
    
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
    def parse_object_detail_info(data: str, include_image: bool = False) -> DetectedObject:
        """객체 정보 파싱"""
        try:
            # MR_OD:OK,{object_id},{object_type},{zone},{timestamp},{image_data} 형식 파싱
            if not data.startswith(f"{MessagePrefix.MR_OD.value}:OK,"):
                raise ValueError(f"잘못된 메시지 형식: {data}")
                
            fields = data.replace(f"{MessagePrefix.MR_OD.value}:OK,", '').split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
            if len(fields) != 5:  # MR_OD:OK, 제외하고 5개 필드
                raise ValueError(f"필드 수 오류: {len(fields)} != 5")
            
            # 필수 필드 파싱
            parsed_data = {
                'object_id': int(fields[0]),
                'object_type': MessageParser._parse_object_type(fields[1]),
                'zone': MessageParser._parse_zone(fields[2]),
                'timestamp': MessageParser._parse_timestamp(fields[3]),
                'image_data': MessageParser._parse_image_data(fields[4]) if include_image else None,
                'x_coord': 0.0,  # 기본값 설정
                'y_coord': 0.0   # 기본값 설정
            }
            
            return DetectedObject(**parsed_data)
            
        except Exception as e:
            raise ParseError(f"객체 정보 파싱 실패: {e}") from e
    
    @staticmethod
    def _parse_required_fields(fields: List[str]) -> Dict[str, Any]:
        """필수 필드 파싱"""
        try:
            return {
                'object_id': int(fields[0]),
                'object_type': MessageParser._parse_object_type(fields[1]),
                'x_coord': float(fields[2]),
                'y_coord': float(fields[3]),
                'zone': MessageParser._parse_zone(fields[4]),
                'timestamp': MessageParser._parse_timestamp(fields[5])
            }
        except (ValueError, IndexError) as e:
            raise ParseError(f"필수 필드 파싱 실패: {e}") from e
    
    @staticmethod
    def _parse_optional_fields(fields: List[str], include_image: bool) -> Dict[str, Any]:
        """선택적 필드 파싱"""
        result = {
            'extra_info': None,
            'image_data': None
        }
        
        if not fields:
            return result
        
        try:          
            # 이미지 데이터 처리
            if include_image and fields:
                for i, field in enumerate(fields):
                    if field.startswith('data:image/') or MessageParser._is_base64_image(field):
                        result['image_data'] = MessageParser._parse_image_data(field)
                        # 이미지 이전 필드들을 extra_info로 처리
                        if i > 0:
                            result['extra_info'] = ','.join(fields[:i])
                        break
                else:
                    # 이미지가 없는 경우 모든 필드를 extra_info로
                    result['extra_info'] = ','.join(fields)
            else:
                # include_image가 False인 경우
                result['extra_info'] = ','.join(fields)
                
        except Exception as e:
            logger.warning(f"선택적 필드 파싱 경고: {e}")
        
        return result
    
    @staticmethod
    def _parse_object_type(type_str: str) -> ObjectType:
        """객체 타입 파싱"""
        try:
            # 정수인 경우
            type_id = int(type_str)
            return Constants.OBJECT_CLASS_MAPPING[type_id]
        except ValueError:
            # 문자열인 경우
            type_str_lower = type_str.lower()
                      
            # ObjectType enum과 매칭
            for obj_type in ObjectType:
                if obj_type.value.lower() == type_str_lower:
                    return obj_type
            
            # enum 이름으로 시도
            try:
                return ObjectType[type_str.upper()]
            except KeyError:
                raise ValueError(f"객체 타입 오류: {type_str}")
    
    @staticmethod
    def _parse_zone(zone_str: str) -> AirportZone:
        """구역 파싱"""
        try:
            # 정수인 경우
            zone_id = int(zone_str)
            return Constants.ZONE_MAPPING[zone_id]
        except ValueError:
            # 문자열인 경우
            try:
                return AirportZone[zone_str.upper()]
            except KeyError:
                raise ValueError(f"구역 이름 오류: {zone_str}")
    
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
       
    @staticmethod
    def _is_base64_image(field: str) -> bool:
        """Base64 이미지 데이터인지 확인"""
        return field.startswith('data:image/') or (len(field) > 100 and field.replace('=', '').isalnum())
    
    @staticmethod
    def _parse_image_data(field: str) -> bytes:
        """이미지 데이터 파싱"""
        try:
            if field.startswith('data:image/'):
                if ',' not in field:
                    raise ValueError("잘못된 이미지 데이터 형식: 콤마(,)가 없습니다.")
                _, base64_data = field.split(',', 1)
                return base64.b64decode(base64_data)
            else:
                return base64.b64decode(field)
        except Exception as e:
            raise ValueError(f"이미지 데이터 파싱 실패: {e}") from e

    @staticmethod
    def parse_object_info_for_event(data: str) -> DetectedObject:
        """
        객체 감지 이벤트(ME_OD:)용 파서
        포맷: {object_id},{object_type},{x_coord},{y_coord},{zone},{timestamp}
        """
        try:
            fields = data.split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
            if len(fields) < 6:
                raise ValueError(f"필드 수 오류: {len(fields)} < 6")
            return DetectedObject(
                object_id=int(fields[0]),
                object_type=MessageParser._parse_object_type(fields[1]),
                x_coord=float(fields[2]),
                y_coord=float(fields[3]),
                zone=MessageParser._parse_zone(fields[4]),
                timestamp=MessageParser._parse_timestamp(fields[5])
            )
        except Exception as e:
            raise ParseError(f"객체 감지 이벤트 파싱 실패: {e}") from e


class MessageInterface:
    """개선된 TCP 메시지 인터페이스 클래스"""
    
    @staticmethod
    def validate_object_info(object_id: int, object_type: ObjectType, x_coord: float, 
                           y_coord: float, zone: AirportZone, timestamp: float) -> bool:
        """객체 정보 유효성 검증"""
        try:
            validators = [
                lambda: isinstance(object_id, int) and object_id >= 0,
                lambda: isinstance(object_type, ObjectType),
                lambda: isinstance(x_coord, (int, float)) and isinstance(y_coord, (int, float)),
                lambda: isinstance(zone, AirportZone),
                lambda: isinstance(timestamp, (int, float)) and timestamp >= 0
            ]
            
            return all(validator() for validator in validators)
            
        except Exception:
            return False
    
    @staticmethod
    def validate_bird_risk_level(risk_level: int) -> bool:
        """조류 위험도 값 유효성 검증"""
        return risk_level in Constants.BIRD_RISK_MAPPING
    
    @staticmethod
    def validate_runway_risk_level(risk_level: int) -> bool:
        """활주로 위험도 값 유효성 검증"""
        return risk_level in Constants.RUNWAY_RISK_MAPPING
    
    @staticmethod
    def parse_object_detail_info(object_str: str, include_image: bool = False) -> DetectedObject:
        """객체 정보 문자열 파싱 (호환성 유지)"""
        return MessageParser.parse_object_detail_info(object_str, include_image)
    
    @staticmethod
    def parse_message(message: str) -> tuple[MessagePrefix, str]:
        """메시지 파싱"""
        if not message or Constants.Protocol.MESSAGE_SEPARATOR not in message:
            raise ParseError(f"메시지 포맷 오류: {message}")
            
        parts = message.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
        if len(parts) != 2:
            raise ParseError(f"메시지 포맷 오류: {message}")
        
        prefix_str, data = parts
        try:
            prefix = MessagePrefix(prefix_str)
        except ValueError:
            raise ParseError(f"알 수 없는 메시지 프리픽스: {prefix_str}")
        
        return prefix, data
    
    @staticmethod
    def parse_object_detection_event(data: str) -> List[DetectedObject]:
        """객체 감지 이벤트 메시지 파싱"""
        if not data.strip():
            return []
        objects = []
        object_records = data.split(Constants.Protocol.OBJECT_RECORD_SEPARATOR)
        for record in object_records:
            if record.strip():
                try:
                    obj_info = MessageParser.parse_object_info_for_event(record.strip())
                    objects.append(obj_info)
                except Exception as e:
                    logger.error(f"객체 정보 파싱 오류: {e}")
                    continue
        return objects
    
    @staticmethod
    def parse_bird_risk_level_event(data: str) -> BirdRiskLevel:
        """조류 위험도 변경 이벤트 메시지 파싱"""
        try:
            risk_level = int(data.strip())
        except ValueError:
            raise ParseError(f"조류 위험도 값 오류: {data}")
            
        if not MessageInterface.validate_bird_risk_level(risk_level):
            raise ParseError(f"조류 위험도 값 오류: {risk_level}")
            
        return Constants.BIRD_RISK_MAPPING[risk_level]
    
    @staticmethod
    def parse_runway_risk_level_event(data: str) -> RunwayRiskLevel:
        """활주로 위험도 변경 이벤트 메시지 파싱"""
        try:
            risk_level = int(data.strip())
        except ValueError:
            raise ParseError(f"활주로 위험도 값 오류: {data}")
            
        if not MessageInterface.validate_runway_risk_level(risk_level):
            raise ParseError(f"활주로 위험도 값 오류: {risk_level}")
            
        return Constants.RUNWAY_RISK_MAPPING[risk_level]
    
    @staticmethod
    def create_message(prefix: MessagePrefix, **kwargs) -> str:
        """메시지 생성"""
        try:
            format_str = Constants.Protocol.MESSAGE_FORMAT[prefix]
            return format_str.format(prefix=prefix.value, **kwargs)
        except KeyError as e:
            raise ProtocolError(f"알 수 없는 메시지 프리픽스: {prefix}") from e
        except Exception as e:
            raise ProtocolError(f"메시지 생성 실패: {e}") from e

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
        if isinstance(error, ConnectionError):
            ErrorHandler._handle_connection_error(error, context)
        elif isinstance(error, ParseError):
            ErrorHandler._handle_parse_error(error, context)
        elif isinstance(error, ProtocolError):
            ErrorHandler._handle_protocol_error(error, context)
        else:
            ErrorHandler._handle_generic_error(error, context)
    
    @staticmethod
    def _handle_connection_error(error: ConnectionError, context: str) -> None:
        """연결 에러 처리"""
        logger.error(f"연결 오류 [{context}]: {error}")
    
    @staticmethod
    def _handle_parse_error(error: ParseError, context: str) -> None:
        """파싱 에러 처리"""
        logger.error(f"파싱 오류 [{context}]: {error}")
    
    @staticmethod
    def _handle_protocol_error(error: ProtocolError, context: str) -> None:
        """프로토콜 에러 처리"""
        logger.error(f"프로토콜 오류 [{context}]: {error}")
    
    @staticmethod
    def _handle_generic_error(error: Exception, context: str) -> None:
        """일반 에러 처리"""
        logger.error(f"일반 오류 [{context}]: {error}")


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
            'is_healthy': self._is_system_healthy(),
            'reconnect_attempts': self.reconnect_attempts
        }
    
    def _is_system_healthy(self) -> bool:
        """시스템 건강 상태 확인"""
        return (self.tcp_state == ConnectionState.CONNECTED and 
                self.udp_state == ConnectionState.CONNECTED)
    
    def reset_reconnect_attempts(self):
        """재연결 시도 횟수 리셋"""
        self.reconnect_attempts = 0
    
    def increment_reconnect_attempts(self) -> bool:
        """재연결 시도 횟수 증가, 최대 시도 횟수 초과 여부 반환"""
        self.reconnect_attempts += 1
        return self.reconnect_attempts >= self.max_reconnect_attempts
