from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
from config import ObjectType, BirdRiskLevel, RunwayRiskLevel, AirportZone, MessagePrefix, Constants
from models.detected_object import DetectedObject

class MessageInterface:
    """TCP 메시지 인터페이스 클래스"""
    
    @staticmethod
    def validate_object_info(object_id: int, object_type: int, x_coord: float, 
                           y_coord: float, zone: int, timestamp: float) -> bool:
        """객체 정보 유효성 검증"""
        try:
            # ID 검증
            if not isinstance(object_id, int) or object_id < 0:
                return False
            
            # 타입 검증 - Constants 매핑 사용
            if object_type not in Constants.OBJECT_CLASS_MAPPING:
                return False
            
            # 좌표 검증
            if not isinstance(x_coord, (int, float)) or not isinstance(y_coord, (int, float)):
                return False
            
            # 구역 검증 - Constants 매핑 사용
            if zone not in Constants.ZONE_MAPPING:
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
        fields = object_str.split(Constants.OBJECT_FIELD_SEPARATOR)
        
        if len(fields) < 6:
            raise ValueError("Insufficient object info fields")
        
        # 안전한 변환
        try:
            object_id = int(fields[0])
            object_type_id = int(fields[1])
            x_coord = float(fields[2])
            y_coord = float(fields[3])
            zone_id = int(fields[4])
            timestamp_val = float(fields[5])
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid field format: {e}")
        
        # 매핑을 통한 변환
        if object_type_id not in Constants.OBJECT_CLASS_MAPPING:
            raise ValueError(f"Invalid object type: {object_type_id}")
        if zone_id not in Constants.ZONE_MAPPING:
            raise ValueError(f"Invalid zone: {zone_id}")
            
        object_type = Constants.OBJECT_CLASS_MAPPING[object_type_id]
        zone = Constants.ZONE_MAPPING[zone_id]
        
        # 타임스탬프 변환
        try:
            timestamp = datetime.fromtimestamp(timestamp_val)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp: {e}")
        
        # 데이터 검증
        if not MessageInterface.validate_object_info(
            object_id, object_type_id, x_coord, y_coord, zone_id, timestamp_val
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
        if not message or Constants.MESSAGE_SEPARATOR not in message:
            raise ValueError(f"Invalid message format: {message}")
            
        parts = message.split(Constants.MESSAGE_SEPARATOR, 1)
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
        object_records = data.split(Constants.OBJECT_RECORD_SEPARATOR)
        
        for record in object_records:
            if record.strip():
                try:
                    obj_info = MessageInterface.parse_object_info(record.strip())
                    objects.append(obj_info)
                except Exception as e:
                    print(f"객체 정보 파싱 오류: {e}")
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
        format_str = Constants.MESSAGE_FORMAT[prefix]
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
        prefix = MessagePrefix.MC_CA if camera_id == "A" else MessagePrefix.MC_CB
        return MessageInterface.create_message(prefix)
    
    @staticmethod
    def create_map_request() -> str:
        """지도 영상 요청 메시지 생성"""
        return MessageInterface.create_message(MessagePrefix.MC_MP)