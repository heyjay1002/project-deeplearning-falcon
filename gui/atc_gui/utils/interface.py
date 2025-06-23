from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
from dataclasses import dataclass, field
from enum import Enum
from config.constants import ObjectType, BirdRiskLevel, RunwayRiskLevel, Airportarea, MessagePrefix, Constants
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
    """개선된 감지 객체 정보를 저장하는 데이터 클래스"""
    object_id: int
    object_type: ObjectType
    x_coord: float
    y_coord: float
    zone: Airportarea
    timestamp: Optional[datetime] = None
    extra_info: Optional[str] = None  # str로 변경
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
        if self.timestamp is not None and not isinstance(self.timestamp, datetime):
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
            'extra_info': self.extra_info,
            'image_data': self.image_base64
        }

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
    def parse_object_detail_info(data: str, image_data: bytes) -> DetectedObject:
        # MR_OD:OK,{object_id},{object_type},{area},{timestamp},{image_size},{image_data} 형식 파싱
        if not data.startswith(f"{MessagePrefix.MR_OD.value}:OK,"):
            raise ValueError(f"잘못된 메시지 형식: {data}")
            
        # --- 추가: 서버에서 받은 원본 텍스트 데이터 info 로그 ---
        logger.info(f"MR_OD: 원본 텍스트 데이터(이미지 제외): {data}")
        # ---
        fields = data.replace(f"{MessagePrefix.MR_OD.value}:OK,", '').split(Constants.Protocol.OBJECT_FIELD_SEPARATOR)
        logger.error(f"MR_OD: 수신 row(이미지 제외): {fields}")
        if len(fields) != 6:
            logger.error(f"MR_OD: 응답 필드 수 부족: {len(fields)} / row={fields}")
            raise ValueError(f"필드 수 오류: {len(fields)} != 6")
            
        object_id = int(fields[0])
        object_type = MessageParser._parse_object_type(fields[1])
        zone = MessageParser._parse_zone(fields[2])
        timestamp = MessageParser._parse_timestamp(fields[3])
        image_size = int(fields[4])
        
        # image_data는 별도로 전달받은 바이너리 데이터 사용
        if len(image_data) != image_size:
            logger.warning(f"이미지 크기 불일치: {len(image_data)} != {image_size}")
            
        return DetectedObject(
            object_id=object_id,
            object_type=object_type,
            x_coord=0.0,  # 상세 정보에는 좌표가 없음
            y_coord=0.0,
            zone=zone,
            timestamp=timestamp,
            image_data=image_data
        )
    
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
            }
        except (ValueError, IndexError) as e:
            raise Exception(f"필수 필드 파싱 실패: {e}") from e
    
    @staticmethod
    def _parse_optional_fields(fields: List[str], include_image: bool) -> Dict[str, Any]:
        """선택적 필드 파싱"""
        result = {
            'timestamp': MessageParser._parse_timestamp(fields[4]),
            'extra_info': None,
            'image_size': int(fields[5]),
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
    def _parse_zone(zone_str: str) -> Airportarea:
        """구역 파싱"""
        try:
            # 정수인 경우
            zone_id = int(zone_str)
            return Constants.area_MAPPING[zone_id]
        except ValueError:
            # 문자열인 경우
            try:
                return Airportarea[zone_str.upper()]
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
                object_type=ObjectType[fields[1]],
                x_coord=float(fields[2]),
                y_coord=float(fields[3]),
                zone=Airportarea(fields[4]),
                timestamp=MessageParser._parse_timestamp(fields[5])
            )
        except Exception as e:
            raise Exception(f"객체 감지 이벤트 파싱 실패: {e}") from e


class MessageInterface:
    """개선된 TCP 메시지 인터페이스 클래스"""
    
    @staticmethod
    def validate_object_info(object_id: int, object_type: ObjectType, x_coord: float, 
                           y_coord: float, zone: Airportarea, timestamp: float) -> bool:
        """객체 정보 유효성 검증"""
        try:
            validators = [
                lambda: isinstance(object_id, int) and object_id >= 0,
                lambda: isinstance(object_type, ObjectType),
                lambda: isinstance(x_coord, (int, float)) and isinstance(y_coord, (int, float)),
                lambda: isinstance(zone, Airportarea),
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
    def parse_object_detection_event(payload: str) -> List[DetectedObject]:
        """객체 감지 이벤트 파싱 - 여러 객체 지원"""
        objects = []
        
        logger.debug(f"객체 감지 이벤트 파싱 시작: {payload[:200]}...")
        
        # 여러 객체가 ;로 구분된 경우 처리
        object_records = payload.split(';')
        logger.debug(f"분리된 객체 레코드 수: {len(object_records)}")
        
        for i, record in enumerate(object_records):
            if not record.strip():
                logger.debug(f"빈 레코드 건너뜀: 인덱스 {i}")
                continue
                
            logger.debug(f"객체 레코드 {i+1} 처리: {record}")
            
            try:
                parts = record.split(',')
                if len(parts) < 5:  # 최소 필수 필드: id, type, x, y, zone
                    logger.warning(f"객체 레코드 필드 수 부족: {len(parts)} < 5, 레코드: {record}")
                    continue
                
                # 기본 필드 파싱 (필수)
                object_id = int(parts[0])
                object_type_str = parts[1]
                x_coord = float(parts[2])
                y_coord = float(parts[3])
                zone_str = parts[4]
                
                logger.debug(f"기본 필드 파싱: ID={object_id}, Type={object_type_str}, Pos=({x_coord},{y_coord}), Zone={zone_str}")
                
                # ObjectType 파싱 - 한글 value와 영문 key 모두 처리
                try:
                    object_type = ObjectType[object_type_str]
                    logger.debug(f"ObjectType 영문 key로 파싱 성공: {object_type.value}")
                except KeyError:
                    # 한글 value로 시도
                    for obj_type in ObjectType:
                        if obj_type.value == object_type_str:
                            object_type = obj_type
                            logger.debug(f"ObjectType 한글 value로 파싱 성공: {object_type.value}")
                            break
                    else:
                        logger.warning(f"알 수 없는 객체 타입: {object_type_str}")
                        continue
                
                # Airportarea 파싱 - 한글 value와 영문 key 모두 처리
                try:
                    zone = Airportarea[zone_str]
                    logger.debug(f"Airportarea 영문 key로 파싱 성공: {zone.value}")
                except KeyError:
                    # 한글 value로 시도
                    for zone_type in Airportarea:
                        if zone_type.value == zone_str:
                            zone = zone_type
                            logger.debug(f"Airportarea 한글 value로 파싱 성공: {zone.value}")
                            break
                    else:
                        logger.warning(f"알 수 없는 구역: {zone_str}")
                        continue
                
                # 타임스탬프 처리 (선택적)
                if len(parts) > 5 and parts[5].strip():
                    try:
                        timestamp_str = parts[5].strip()
                        if 'T' in timestamp_str:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        else:
                            timestamp = datetime.fromtimestamp(float(timestamp_str))
                        logger.debug(f"타임스탬프 파싱 성공: {timestamp}")
                    except (ValueError, OSError):
                        logger.warning(f"타임스탬프 형식 오류")
                        timestamp =None
                else:
                    logger.debug("타임스탬프 정보 없음")
                    timestamp = None
                
                # 이미지 데이터 처리 (선택적)
                image_data = None
                if len(parts) > 6 and parts[6].strip():
                    try:
                        image_b64 = parts[6].strip()
                        # Base64 패딩 추가
                        missing_padding = len(image_b64) % 4
                        if missing_padding:
                            image_b64 += '=' * (4 - missing_padding)
                        image_data = base64.b64decode(image_b64)
                        logger.debug(f"이미지 데이터 파싱 성공: {len(image_data)} bytes")
                    except Exception as e:
                        logger.debug(f"이미지 데이터 파싱 실패: {e}")
                        image_data = None
                
                # DetectedObject 생성
                obj = DetectedObject(
                    object_id=object_id,
                    object_type=object_type,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    zone=zone,
                    timestamp=timestamp,
                    extra_info=None,
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
        """메시지 생성"""
        try:
            format_str = Constants.Protocol.MESSAGE_FORMAT[prefix]
            return format_str.format(prefix=prefix.value, **kwargs)
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
