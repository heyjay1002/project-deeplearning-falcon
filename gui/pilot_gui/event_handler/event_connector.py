from typing import Dict, Callable, Optional, Any

# 통합된 TCP 클라이언트 사용
from network import TCPClient
from simulator import TCPSimulator

class EventManager:
    """
    이벤트 관리 및 핸들러 등록
    
    TCP 서버로부터 이벤트를 수신하고, 등록된 핸들러에게 전달합니다.
    """
    
    def __init__(self, server_host: str = "localhost", server_port: int = 5300, use_simulator: bool = True):
        """
        이벤트 매니저 초기화
        
        Args:
            server_host: TCP 서버 호스트
            server_port: TCP 서버 포트
            use_simulator: 연결 실패 시 시뮬레이터 사용 여부
        """
        # 통합된 TCP 클라이언트 사용
        self.tcp_client = TCPClient(server_host, server_port)
        self.use_simulator = use_simulator
        
        # 시뮬레이터 초기화
        if use_simulator:
            self.simulator = TCPSimulator()
        else:
            self.simulator = None
        
        print(f"[EventManager] 초기화 완료: {server_host}:{server_port}")
    
    def connect(self) -> bool:
        """
        TCP 서버에 연결하고 이벤트 수신 시작
        
        Returns:
            연결 성공 여부
        """
        success = self.tcp_client.connect()
        if success:
            print(f"[EventManager] ✅ 서버 연결 성공")
        else:
            print(f"[EventManager] ❌ 서버 연결 실패")
            if self.use_simulator:
                print(f"[EventManager] 🔄 시뮬레이터로 폴백")
        return success
    
    def disconnect(self):
        """서버 연결 해제"""
        self.tcp_client.disconnect()
        print(f"[EventManager] 연결 해제 완료")
    
    def register_handler(self, event_name: str, handler: Callable):
        """
        이벤트 핸들러 등록
        
        Args:
            event_name: 이벤트 이름 (BR_CHANGED, RUNWAY_ALPHA_STATUS_CHANGED 등)
            handler: 이벤트 처리 함수 (event_data: dict를 인자로 받음)
        """
        self.tcp_client.register_event_handler(event_name, handler)
        print(f"[EventManager] 이벤트 핸들러 등록: {event_name}")
    
    def unregister_handler(self, event_name: str):
        """
        이벤트 핸들러 해제
        
        Args:
            event_name: 이벤트 이름
        """
        self.tcp_client.unregister_event_handler(event_name)
        print(f"[EventManager] 이벤트 핸들러 해제: {event_name}")
    
    def get_registered_events(self) -> list:
        """
        등록된 이벤트 목록 반환
        
        Returns:
            등록된 이벤트 이름 리스트
        """
        return self.tcp_client.get_registered_events()
    
    def is_connected(self) -> bool:
        """
        연결 상태 확인
        
        Returns:
            연결 상태
        """
        return self.tcp_client.is_connected()
    
    def get_status(self) -> Dict[str, Any]:
        """
        이벤트 매니저 상태 정보 반환
        
        Returns:
            상태 정보 딕셔너리
        """
        status = self.tcp_client.get_server_status()
        status["registered_events"] = self.get_registered_events()
        return status
    
    def handle_event(self, event_message: dict):
        """
        이벤트 처리
        
        Args:
            event_message: 이벤트 메시지
        """
        try:
            # TCP 서버에서 이벤트 수신
            if self.is_connected():
                self._notify_handlers(event_message)
            elif self.use_simulator and self.simulator:
                # 시뮬레이터에서 이벤트 생성
                event_type = event_message.get("event")
                simulator_event = self.simulator.generate_event(event_type)
                if simulator_event:
                    self._notify_handlers(simulator_event)
        except Exception as e:
            print(f"[EventManager] ❌ 이벤트 처리 오류: {e}")
    
    def _notify_handlers(self, event_message: dict):
        """
        등록된 핸들러에게 이벤트 전달
        
        Args:
            event_message: 이벤트 메시지
        """
        event_name = event_message.get("event")
        if event_name in self.tcp_client.event_handlers:
            for handler in self.tcp_client.event_handlers[event_name]:
                try:
                    handler(event_message)
                except Exception as e:
                    print(f"[EventManager] ❌ 핸들러 실행 오류: {e}")