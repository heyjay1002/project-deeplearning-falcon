from typing import Dict, Any, Tuple
from .remote_client import RemoteServerClient
from .local_mock import LocalMockServer

class HybridClient:
    """
    원격 서버 + 로컬 모의 서버 폴백을 지원하는 하이브리드 클라이언트
    """
    
    def __init__(self, server_url: str = "http://localhost:8000", use_mock_fallback: bool = True):
        """
        하이브리드 클라이언트 초기화
        
        Args:
            server_url: 원격 서버 URL
            use_mock_fallback: 원격 서버 실패 시 로컬 모의 서버 사용 여부
        """
        self.remote_client = RemoteServerClient(server_url)
        self.local_mock = LocalMockServer() if use_mock_fallback else None
        self.use_mock_fallback = use_mock_fallback
        self.server_available = False
        
        # 서버 연결 상태 확인
        self._check_server_availability()
    
    def _check_server_availability(self):
        """서버 연결 상태 확인"""
        self.server_available = self.remote_client.test_connection()
        
        if self.server_available:
            print(f"[HybridClient] ✅ 원격 서버 사용")
        elif self.use_mock_fallback:
            print(f"[HybridClient] 🔄 로컬 모의 서버로 폴백")
        else:
            print(f"[HybridClient] ❌ 서버 사용 불가")
    
    def send_query(self, request_code: str, parameters: Dict[str, Any], session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        질의 전송 (원격 서버 우선, 실패 시 로컬 모의 서버)
        
        Args:
            request_code: 요청 코드
            parameters: 요청 파라미터  
            session_id: 세션 ID
            
        Returns:
            (성공 여부, 응답 데이터) 튜플
        """
        # 1. 원격 서버 시도
        if self.server_available:
            success, result = self.remote_client.send_query(request_code, parameters, session_id)
            if success:
                return True, result
            else:
                print(f"[HybridClient] 원격 서버 실패, 폴백 시도...")
                self.server_available = False
        
        # 2. 로컬 모의 서버 폴백
        if self.use_mock_fallback and self.local_mock:
            intent = self.remote_client.intent_mapping.get(request_code, "unknown_request")
            structured_params = self.remote_client._structure_parameters(request_code, parameters)
            
            mock_result = self.local_mock.process_query(intent, structured_params)
            mock_result["session_id"] = session_id
            mock_result["source"] = "local_mock"
            
            print(f"[HybridClient] 🔄 로컬 모의 서버 응답 생성")
            return True, mock_result
        
        # 3. 모든 방법 실패
        return False, {
            "error": "all_servers_failed",
            "message": "원격 서버와 로컬 모의 서버 모두 사용할 수 없습니다."
        } 