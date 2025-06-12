import requests
import json
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from .local_mock import LocalMockServer

class ServerClient:
    """
    원격 서버 통신 + 로컬 모의 서버 폴백을 지원하는 통합 클라이언트
    Confluence 문서 기준 통신 프로토콜 사용
    """
    
    def __init__(self, server_url: str = "http://localhost:8000", use_mock_fallback: bool = True):
        """
        서버 클라이언트 초기화
        
        Args:
            server_url: 원격 서버 URL
            use_mock_fallback: 원격 서버 실패 시 로컬 모의 서버 사용 여부
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = 30  # 30초 타임아웃
        self.session = requests.Session()
        self.use_mock_fallback = use_mock_fallback
        self.server_available = False
        
        # 로컬 모의 서버 (옵션)
        self.local_mock = LocalMockServer() if use_mock_fallback else None
        
        # Confluence 문서 기준 요청 코드 → 인텐트 매핑
        self.intent_mapping = {
            "BIRD_RISK_INQUIRY": "bird_risk_inquiry",
            "RUNWAY_ALPHA_STATUS": "runway_alpha_status", 
            "RUNWAY_BRAVO_STATUS": "runway_bravo_status",
            "AVAILABLE_RUNWAY_INQUIRY": "available_runway_inquiry"
        }
        
        # 서버 연결 상태 확인
        self._check_server_availability()
        
        print(f"[ServerClient] 초기화 완료: {server_url}")
    
    def _check_server_availability(self):
        """서버 연결 상태 확인"""
        self.server_available = self.test_connection()
        
        if self.server_available:
            print(f"[ServerClient] ✅ 원격 서버 사용")
        elif self.use_mock_fallback:
            print(f"[ServerClient] 🔄 로컬 모의 서버로 폴백")
        else:
            print(f"[ServerClient] ❌ 서버 사용 불가")
    
    def send_query(self, request_code: str, parameters: Dict[str, Any], session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        질의 전송 (원격 서버 우선, 실패 시 로컬 모의 서버)
        
        Args:
            request_code: 요청 코드 (BIRD_RISK_INQUIRY, RUNWAY_ALPHA_STATUS 등)
            parameters: 요청 파라미터
            session_id: 세션 ID
            
        Returns:
            (성공 여부, 응답 데이터) 튜플
        """
        # 1. 원격 서버 시도
        if self.server_available:
            success, result = self._send_remote_query(request_code, parameters, session_id)
            if success:
                return True, result
            else:
                print(f"[ServerClient] 원격 서버 실패, 폴백 시도...")
                self.server_available = False
        
        # 2. 로컬 모의 서버 폴백
        if self.use_mock_fallback and self.local_mock:
            intent = self.intent_mapping.get(request_code, "unknown_request")
            structured_params = self._structure_parameters(request_code, parameters)
            
            mock_result = self.local_mock.process_query(intent, structured_params)
            mock_result["session_id"] = session_id
            mock_result["source"] = "local_mock"
            
            print(f"[ServerClient] 🔄 로컬 모의 서버 응답 생성")
            return True, mock_result
        
        # 3. 모든 방법 실패
        return False, {
            "error": "all_servers_failed",
            "message": "원격 서버와 로컬 모의 서버 모두 사용할 수 없습니다."
        }
    
    def _send_remote_query(self, request_code: str, parameters: Dict[str, Any], session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        원격 서버에 HTTP 질의 전송 (Confluence 문서 기준)
        
        Args:
            request_code: 요청 코드
            parameters: 요청 파라미터
            session_id: 세션 ID
            
        Returns:
            (성공 여부, 응답 데이터) 튜플
        """
        try:
            # 1. 인텐트 변환 (Confluence 문서 기준)
            intent = self.intent_mapping.get(request_code, "unknown_request")
            
            # 2. 파라미터 구조화
            structured_params = self._structure_parameters(request_code, parameters)
            
            # 3. Confluence 문서 기준 페이로드 구성
            payload = {
                "type": "command",
                "command": "query_information", 
                "intent": intent,
                "source": "pilot_gui",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "parameters": structured_params
            }
            
            print(f"[ServerClient] 원격 질의 전송: {intent}")
            print(f"  파라미터: {structured_params}")
            
            # 4. HTTP 요청 전송
            response = self.session.post(
                f"{self.server_url}/api/query",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[ServerClient] ✅ 원격 응답 수신: {result.get('response_code', 'OK')}")
                return True, result
            else:
                print(f"[ServerClient] ❌ HTTP 오류: {response.status_code}")
                return False, {"error": f"HTTP {response.status_code}", "message": response.text}
        
        except requests.exceptions.Timeout:
            print(f"[ServerClient] ⏰ 서버 응답 타임아웃")
            return False, {"error": "timeout", "message": "서버 응답 시간 초과"}
        except requests.exceptions.ConnectionError:
            print(f"[ServerClient] 🔌 서버 연결 실패")
            return False, {"error": "connection_failed", "message": "서버에 연결할 수 없습니다"}
        except Exception as e:
            print(f"[ServerClient] ❌ 예상치 못한 오류: {e}")
            return False, {"error": "unknown_error", "message": str(e)}
    
    def _structure_parameters(self, request_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        요청 파라미터 구조화 (Confluence 문서 기준)
        
        Args:
            request_code: 요청 코드
            parameters: 원본 파라미터
            
        Returns:
            구조화된 파라미터
        """
        structured = {}
        
        # 공통 파라미터
        if "callsign" in parameters:
            structured["callsign"] = parameters["callsign"]
        if "original_text" in parameters:
            structured["original_text"] = parameters["original_text"]
        
        # 요청별 특화 파라미터
        if request_code == "RUNWAY_ALPHA_STATUS":
            structured["runway_id"] = "RWY-ALPHA"
        elif request_code == "RUNWAY_BRAVO_STATUS":
            structured["runway_id"] = "RWY-BRAVO"
        elif request_code == "BIRD_RISK_INQUIRY":
            if "area" in parameters:
                structured["area"] = parameters["area"]
            else:
                structured["area"] = "RWY-15"  # 기본값
        elif request_code == "AVAILABLE_RUNWAY_INQUIRY":
            structured["query_type"] = "all_runways"
        
        return structured
    
    def test_connection(self) -> bool:
        """
        원격 서버 연결 테스트
        
        Returns:
            연결 성공 여부
        """
        try:
            response = self.session.get(
                f"{self.server_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"[ServerClient] ✅ 서버 연결 성공")
                return True
            else:
                print(f"[ServerClient] ⚠️ 서버 응답 이상: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ServerClient] ❌ 연결 테스트 실패: {e}")
            return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        서버 상태 정보 조회
        
        Returns:
            서버 상태 정보
        """
        try:
            response = self.session.get(
                f"{self.server_url}/status",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)} 