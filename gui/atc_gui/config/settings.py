from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerSettings:
    """서버 연결 설정"""
    tcp_ip: str = "192.168.0.8"
    tcp_port: int = 4100
    udp_ip: str = "192.168.0.8"
    udp_port: int = 5100
    connection_timeout: int = 3  # 초 단위
    reconnect_interval: int = 3  # 초 단위
    max_reconnect_attempts: int = 3  # 최대 재연결 시도 횟수
    reconnect_backoff_factor: int = 2  # 재연결 간격 증가 배수
    tcp_buffer_size: int = 4096
    udp_buffer_size: int = 65536
    video_fps: int = 30  # 비디오 프레임 레이트

@dataclass
class AlertSettings:
    """알림 설정"""
    duration: int = 5  # 알림 지속 시간 (초)
    volume: float = 0.8  # 알림음 볼륨 (0.0 ~ 1.0)

@dataclass
class DataSettings:
    """데이터 처리 설정"""
    refresh_interval: int = 100  # 데이터 수신 주기 (밀리초)
    video_buffer_size: int = 10  # 비디오 프레임 버퍼 크기

@dataclass
class LogSettings:
    """로그 설정"""
    file_path: str = "logs/falcon_system.log"
    level: str = "INFO"
    max_size: int = 10  # MB
    backup_count: int = 5
    retention_days: int = 30  # 이력 보관 기간 (일)

@dataclass
class DebugSettings:
    """개발/디버그 설정"""
    debug_mode: bool = True
    sample_data_interval: int = 2  # 샘플 데이터 생성 간격 (초)
    network_debug: bool = True
    video_debug: bool = True  # 비디오 디버그 모드

class Settings:
    """설정 관리 클래스"""
    
    def __init__(self):
        self.server: ServerSettings = ServerSettings()
        self.alert: AlertSettings = AlertSettings()
        self.data: DataSettings = DataSettings()
        self.log: LogSettings = LogSettings()
        self.debug: DebugSettings = DebugSettings()
    
    # 싱글톤 패턴 구현
    _instance: Optional['Settings'] = None
    
    @classmethod
    def get_instance(cls) -> 'Settings':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance 