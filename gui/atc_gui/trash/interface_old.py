from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
from dataclasses import dataclass
from config import ObjectType, BirdRiskLevel, RunwayRiskLevel, AirportZone, MessagePrefix, Constants
from utils.logger import logger

@dataclass
class DetectedObject:
    """감지된 객체 정보를 저장하는 데이터 클래스"""
    object_id: int
    object_type: ObjectType
    x_coord: float
    y_coord: float
    zone: AirportZone
    timestamp: datetime
    extra_info: Optional[Dict[str, Any]] = None
    image_data: Optional[bytes] = None

    def __post_init__(self):
        """데이터 유효성 검증"""
        if not isinstance(self.object_id, int) or self.object_id < 0:
            raise ValueError("Invalid object ID")
        
        if not isinstance(self.x_coord, (int, float)) or not isinstance(self.y_coord, (int, float)):
            raise ValueError("Invalid coordinates")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Invalid timestamp")

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
    def is_fire(self) -> bool:
        """화재 객체 여부 확인"""
        return self.object_type == ObjectType.FIRE

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

    def to_dict(self) -> Dict[str, Any]:
        """객체 정보를 딕셔너리로 변환"""
        return {
            'object_id': self.object_id,
            'object_type': self.object_type.value,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'zone': self.zone.value,
            'timestamp': self.timestamp.isoformat(),
            'extra_info': self.extra_info,
            'image_data': self.image_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectedObject':
        """딕셔너리로부터 객체 생성"""
        return cls(
            object_id=data['object_id'],
            object_type=ObjectType(data['object_type']),
            x_coord=data['x_coord'],
            y_coord=data['y_coord'],
            zone=AirportZone(data['zone']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            extra_info=data.get('extra_info'),
            image_data=data.get('image_data')
        )

    def __str__(self) -> str:
        """객체의 문자열 표현"""
        return (f"Object {self.object_id} ({self.object_type.value}) "
                f"at ({self.x_coord}, {self.y_coord}) in {self.zone.value}")


@dataclass(frozen=True)
class BirdRisk:
    value: int

    def __post_init__(self):
        if self.value not in Constants.BIRD_RISK_MAPPING:
            raise ValueError(f"유효하지 않은 조류 위험도 값: {self.value}")

    @property
    def enum(self) -> BirdRiskLevel:
        return Constants.BIRD_RISK_MAPPING[self.value]

    def __str__(self):
        return f"조류 위험도: {self.enum.value}({self.value})"


@dataclass(frozen=True)
class RunwayRisk:
    runway_id: str  # "A" 또는 "B"
    value: int

    def __post_init__(self):
        if self.runway_id not in ("A", "B"):
            raise ValueError(f"유효하지 않은 활주로 ID: {self.runway_id}")
        if self.value not in Constants.RUNWAY_RISK_MAPPING:
            raise ValueError(f"유효하지 않은 활주로 위험도 값: {self.value}")

    @property
    def enum(self) -> RunwayRiskLevel:
        return Constants.RUNWAY_RISK_MAPPING[self.value]

    def __str__(self):
        return f"활주로 {self.runway_id} 위험도: {self.enum.value}({self.value})"


class MessageInterface:
    """TCP 메시지 인터페이스 클래스"""
    
    @staticmethod
    def validate_object_info(object_id: int, object_type: ObjectType, x_coord: float, 
                           y_coord: float, zone: AirportZone, timestamp: float) -> bool:
        """객체 정보 유효성 검증"""
        try:
            # ID 검증
            if not isinstance(object_id, int) or object_id < 0:
                return False
            
            # 타입 검증
            if not isinstance(object_type, ObjectType):
                return False
            
            # 좌표 검증
            if not isinstance(x_coord, (int, float)) or not isinstance(y_coord, (int, float)):
                return False
            
            # 구역 검증
            if not isinstance(zone, AirportZone):
                return False
            
            # 타임스탬프 검증
            if not isinstance(timestamp, (int, float)) or timestamp < 0:
                return False
            
            return True
            
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
    def parse_object_info(object_str: str, include_image: bool = False) -> DetectedObject:
        """객체 정보 문자열 파싱"""
        fields = object_str.split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
        
        if len(fields) < 6:
            raise ValueError("Insufficient object info fields")
        
        # 안전한 변환
        try:
            object_id = int(fields[0])
            # 객체 타입 처리 (정수 또는 문자열)
            try:
                object_type_id = int(fields[1])
                object_type = Constants.OBJECT_CLASS_MAPPING[object_type_id]
            except ValueError:
                # 문자열인 경우 대소문자 구분 없이 ObjectType enum으로 변환
                type_str = fields[1].lower()  # 소문자로 변환
                # 특수 케이스 처리
                if type_str == 'car':
                    object_type = ObjectType.VEHICLE
                else:
                    # ObjectType enum의 value를 소문자로 변환하여 비교
                    for obj_type in ObjectType:
                        if obj_type.value.lower() == type_str:
                            object_type = obj_type
                            break
                    else:
                        # 직접 enum 이름으로도 시도
                        try:
                            object_type = ObjectType[type_str.upper()]
                        except KeyError:
                            raise ValueError(f"Invalid object type: {fields[1]}")
            x_coord = float(fields[2])
            y_coord = float(fields[3])
            # 구역 처리 (정수 또는 문자열)
            try:
                zone_id = int(fields[4])
                zone = Constants.ZONE_MAPPING[zone_id]
            except ValueError:
                # 문자열인 경우 대소문자 구분 없이 AirportZone enum으로 변환
                zone_str = fields[4].upper()  # 대문자로 변환
                try:
                    zone = AirportZone[zone_str]
                except KeyError:
                    raise ValueError(f"Invalid zone: {fields[4]}")
            timestamp_val = fields[5]  # 타임스탬프를 문자열로 받음
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid field format: {e}")
        
        # 타임스탬프 변환
        try:
            # ISO 8601 형식 처리
            if 'T' in timestamp_val:
                timestamp = datetime.fromisoformat(timestamp_val.replace('Z', '+00:00'))
            else:
                # Unix timestamp 처리
                timestamp = datetime.fromtimestamp(float(timestamp_val))
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp: {e}")
        
        # 데이터 검증
        if not MessageInterface.validate_object_info(
            object_id, object_type, x_coord, y_coord, zone, timestamp.timestamp()
        ):
            raise ValueError("Invalid object info data")
        
        # 추가 정보 파싱
        extra_info = None
        image_data = None
        
        if len(fields) > 6:
            if include_image:
                try:
                    # Base64 디코딩으로 이미지 데이터 처리
                    image_data = base64.b64decode(fields[6])
                except Exception as e:
                    raise ValueError(f"Invalid image data: {e}")
            else:
                extra_info = fields[6]
        
        return DetectedObject(
            object_id=object_id,
            object_type=object_type,
            x_coord=x_coord,
            y_coord=y_coord,
            zone=zone,
            timestamp=timestamp,
            extra_info=extra_info,
            image_data=image_data
        )
    
    @staticmethod
    def parse_message(message: str) -> tuple[MessagePrefix, str]:
        """메시지 파싱"""
        if not message or Constants.Protocol.MESSAGE_SEPARATOR not in message:
            raise ValueError(f"Invalid message format: {message}")
            
        parts = message.split(Constants.Protocol.MESSAGE_SEPARATOR, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid message format: {message}")
        
        prefix_str, data = parts
        try:
            prefix = MessagePrefix(prefix_str)
        except ValueError:
            raise ValueError(f"Unknown message prefix: {prefix_str}")
        
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
                    obj_info = MessageInterface.parse_object_info(record.strip())
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
            raise ValueError(f"Invalid bird risk level format: {data}")
            
        if not MessageInterface.validate_bird_risk_level(risk_level):
            raise ValueError(f"Invalid bird risk level value: {risk_level}")
            
        return Constants.BIRD_RISK_MAPPING[risk_level]
    
    @staticmethod
    def parse_runway_risk_level_event(data: str) -> RunwayRiskLevel:
        """활주로 위험도 변경 이벤트 메시지 파싱"""
        try:
            risk_level = int(data.strip())
        except ValueError:
            raise ValueError(f"Invalid runway risk level format: {data}")
            
        if not MessageInterface.validate_runway_risk_level(risk_level):
            raise ValueError(f"Invalid runway risk level value: {risk_level}")
            
        return Constants.RUNWAY_RISK_MAPPING[risk_level]
    
    @staticmethod
    def create_message(prefix: MessagePrefix, **kwargs) -> str:
        """메시지 생성"""
        format_str = Constants.Protocol.MESSAGE_FORMAT[prefix]
        return format_str.format(prefix=prefix.value, **kwargs)

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
            raise ValueError("Invalid camera ID")
        if camera_id == "A":
            prefix = MessagePrefix.MC_CA
        elif camera_id == "B":
            prefix = MessagePrefix.MC_CB
        return MessageInterface.create_message(prefix)
    
    @staticmethod
    def create_map_request() -> str:
        """지도 영상 요청 메시지 생성"""
        return MessageInterface.create_message(MessagePrefix.MC_MP)