from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from config import ObjectType, AirportZone, BirdRiskLevel

@dataclass
class DetectedObject:
    """감지된 객체 정보를 저장하는 데이터 클래스"""
    object_id: int
    object_type: ObjectType
    x_coord: float
    y_coord: float
    zone: AirportZone
    timestamp: datetime
    risk_level: Optional[BirdRiskLevel] = None
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
    def is_fallen_person(self) -> bool:
        """쓰러진 사람 객체 여부 확인"""
        return self.object_type == ObjectType.FALLEN_PERSON

    def to_dict(self) -> Dict[str, Any]:
        """객체 정보를 딕셔너리로 변환"""
        return {
            'object_id': self.object_id,
            'object_type': self.object_type.value,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'zone': self.zone.value,
            'timestamp': self.timestamp.isoformat(),
            'risk_level': self.risk_level.value if self.risk_level else None,
            'extra_info': self.extra_info
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
            risk_level=BirdRiskLevel(data['risk_level']) if data.get('risk_level') else None,
            extra_info=data.get('extra_info')
        )

    def __str__(self) -> str:
        """객체의 문자열 표현"""
        return (f"Object {self.object_id} ({self.object_type.value}) "
                f"at ({self.x_coord}, {self.y_coord}) in {self.zone.value}")
