from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class RequestStatus(Enum):
    """요청 처리 상태"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RequestPriority(Enum):
    """요청 우선순위"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"

@dataclass
class AudioData:
    """오디오 데이터 모델"""
    audio_bytes: bytes
    sample_rate: int = 16000
    channels: int = 1
    duration: float = 0.0
    format: str = "WAV"
    
    def to_base64(self) -> str:
        """오디오 데이터를 base64로 인코딩"""
        import base64
        return base64.b64encode(self.audio_bytes).decode('utf-8')
    
    @classmethod
    def from_base64(cls, base64_str: str, **kwargs):
        """base64 문자열에서 AudioData 생성"""
        import base64
        audio_bytes = base64.b64decode(base64_str)
        return cls(audio_bytes=audio_bytes, **kwargs)

@dataclass
class STTResult:
    """STT 처리 결과"""
    text: str
    confidence_score: float = 0.0
    language: str = "ko"
    processing_time: float = 0.0
    model_used: str = "whisper"
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """신뢰도가 임계값 이상인지 확인"""
        return self.confidence_score >= threshold

@dataclass
class PilotRequest:
    """조종사 요청 모델"""
    session_id: str
    callsign: str
    original_text: str
    request_code: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: RequestPriority = RequestPriority.NORMAL
    status: RequestStatus = RequestStatus.PENDING
    confidence_score: float = 0.0
    processing_time: float = 0.0
    
    def __post_init__(self):
        """초기화 후 처리"""
        # 우선순위 자동 설정
        if "emergency" in self.original_text.lower() or "비상" in self.original_text:
            self.priority = RequestPriority.EMERGENCY
        elif "urgent" in self.original_text.lower() or "긴급" in self.original_text:
            self.priority = RequestPriority.HIGH
    
    def set_status(self, status: RequestStatus):
        """상태 변경"""
        self.status = status
    
    def add_parameter(self, key: str, value: Any):
        """파라미터 추가"""
        self.parameters[key] = value
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """파라미터 조회"""
        return self.parameters.get(key, default)

@dataclass
class PilotResponse:
    """조종사 응답 모델"""
    session_id: str
    request_code: str
    response_text: str
    response_code: str = "SUCCESS"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    
    def is_success(self) -> bool:
        """성공 응답인지 확인"""
        return self.response_code == "SUCCESS"
    
    def add_data(self, key: str, value: Any):
        """응답 데이터 추가"""
        self.data[key] = value

@dataclass
class VoiceInteraction:
    """음성 상호작용 전체 모델"""
    session_id: str
    callsign: str
    
    # 입력 단계
    audio_input: Optional[AudioData] = None
    stt_result: Optional[STTResult] = None
    
    # 처리 단계
    pilot_request: Optional[PilotRequest] = None
    pilot_response: Optional[PilotResponse] = None
    
    # 출력 단계
    tts_text: str = ""
    audio_output: Optional[AudioData] = None
    
    # 메타데이터
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    total_processing_time: float = 0.0
    status: RequestStatus = RequestStatus.PENDING
    error_message: Optional[str] = None
    
    def mark_completed(self):
        """상호작용 완료 표시"""
        self.end_time = datetime.now().isoformat()
        self.status = RequestStatus.COMPLETED
        
        # 총 처리 시간 계산
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.total_processing_time = (end - start).total_seconds()
    
    def mark_failed(self, error_message: str):
        """상호작용 실패 표시"""
        self.end_time = datetime.now().isoformat()
        self.status = RequestStatus.FAILED
        self.error_message = error_message
    
    def get_summary(self) -> Dict[str, Any]:
        """상호작용 요약 정보 반환"""
        return {
            "session_id": self.session_id,
            "callsign": self.callsign,
            "request_text": self.stt_result.text if self.stt_result else "",
            "request_code": self.pilot_request.request_code if self.pilot_request else "",
            "response_text": self.pilot_response.response_text if self.pilot_response else "",
            "status": self.status.value,
            "processing_time": self.total_processing_time,
            "confidence_score": self.stt_result.confidence_score if self.stt_result else 0.0,
            "timestamp": self.start_time,
            "error": self.error_message
        }

@dataclass
class SystemStatus:
    """시스템 상태 모델"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 각 모듈 상태
    audio_io_status: str = "UNKNOWN"
    stt_engine_status: str = "UNKNOWN"
    query_parser_status: str = "UNKNOWN"

    tts_engine_status: str = "UNKNOWN"
    session_manager_status: str = "UNKNOWN"
    
    # 전체 시스템 상태
    overall_status: str = "UNKNOWN"
    
    # 성능 메트릭
    active_sessions: int = 0
    total_interactions_today: int = 0
    average_response_time: float = 0.0
    
    # 오류 정보
    recent_errors: List[str] = field(default_factory=list)
    
    def update_module_status(self, module: str, status: str):
        """모듈 상태 업데이트"""
        setattr(self, f"{module}_status", status)
        self._update_overall_status()
    
    def _update_overall_status(self):
        """전체 상태 업데이트"""
        statuses = [
            self.audio_io_status,
            self.stt_engine_status,
            self.query_parser_status,

            self.tts_engine_status,
            self.session_manager_status
        ]
        
        if all(status == "OPERATIONAL" for status in statuses):
            self.overall_status = "OPERATIONAL"
        elif any(status == "FAILED" for status in statuses):
            self.overall_status = "FAILED"
        elif any(status == "WARNING" for status in statuses):
            self.overall_status = "WARNING"
        else:
            self.overall_status = "UNKNOWN"
    
    def add_error(self, error_message: str):
        """오류 메시지 추가"""
        self.recent_errors.append(f"{datetime.now().isoformat()}: {error_message}")
        # 최근 10개 오류만 유지
        if len(self.recent_errors) > 10:
            self.recent_errors = self.recent_errors[-10:]

# 편의 함수들
def create_pilot_request(session_id: str, callsign: str, text: str, 
                        request_code: str, parameters: Dict[str, Any] = None) -> PilotRequest:
    """PilotRequest 생성 편의 함수"""
    return PilotRequest(
        session_id=session_id,
        callsign=callsign,
        original_text=text,
        request_code=request_code,
        parameters=parameters or {}
    )

def create_pilot_response(session_id: str, request_code: str, 
                         response_text: str, processing_time: float = 0.0) -> PilotResponse:
    """PilotResponse 생성 편의 함수"""
    return PilotResponse(
        session_id=session_id,
        request_code=request_code,
        response_text=response_text,
        processing_time=processing_time
    )
