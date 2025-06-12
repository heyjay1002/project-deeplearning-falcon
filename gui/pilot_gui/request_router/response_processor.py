import json
import time
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class ResponseProcessor:
    """
    메인 서버 응답 처리 및 자연어 응답 생성
    Confluence 문서 기준 RESPONSE_TYPE 테이블 사용
    """
    
    def __init__(self):
        """응답 처리기 초기화 - Confluence 문서 기준 표준 응답 테이블 로드"""
        
        # Confluence 문서 기준 표준 응답 테이블 (RESPONSE_TYPE)
        self.standard_responses = {
            # 조류 위험도 응답 - Confluence 문서 기준
            "BIRD_RISK_HIGH": "Bird activity high. Hold for approach.",
            "BIRD_RISK_MEDIUM": "Bird activity moderate. Be advised.",
            "BIRD_RISK_LOW": "Bird activity low. Clear to proceed.",
            
            # 활주로 상태 응답 - Confluence 문서 기준
            "RWY_A_CLEAR": "Runway Alfa available for landing.",
            "RWY_A_BLOCKED": "Runway Alfa blocked. Use alternate runway.",
            "RWY_B_CLEAR": "Runway Bravo available for landing.",
            "RWY_B_BLOCKED": "Runway Bravo blocked. Use alternate runway.",
            
            # 사용 가능한 활주로 목록 응답 - Confluence 문서 기준
            "AVAILABLE_RUNWAYS_ALL": "Available runways Alfa, Bravo.",
            "AVAILABLE_RUNWAYS_A_ONLY": "Runway Alfa available.",
            "AVAILABLE_RUNWAYS_B_ONLY": "Runway Bravo available.",
            "NO_RUNWAYS_AVAILABLE": "No runways available. Hold for approach.",
            
            # 오류 응답
            "UNRECOGNIZED_COMMAND": "Unable to process request. Say again.",
            "TIMEOUT": "Communication timeout. Try again.",
            "NO_DATA_AVAILABLE": "No data available. Contact tower.",
            "INVALID_AREA": "Invalid area specified. Contact tower.",
            "PARTIAL_RESPONSE": "Partial data received. Contact tower."
        }
        
        # Confluence 문서 기준 응답 코드 설명
        self.response_descriptions = {
            "BIRD_RISK_HIGH": "조류 위험도 높음 - 착륙 대기 필요",
            "BIRD_RISK_MEDIUM": "조류 위험도 보통 - 주의 필요",
            "BIRD_RISK_LOW": "조류 위험도 낮음 - 진행 가능",
            "RWY_A_CLEAR": "활주로 알파 사용 가능",
            "RWY_A_BLOCKED": "활주로 알파 차단됨",
            "RWY_B_CLEAR": "활주로 브라보 사용 가능", 
            "RWY_B_BLOCKED": "활주로 브라보 차단됨",
            "AVAILABLE_RUNWAYS_ALL": "모든 활주로 사용 가능",
            "AVAILABLE_RUNWAYS_A_ONLY": "활주로 알파만 사용 가능",
            "AVAILABLE_RUNWAYS_B_ONLY": "활주로 브라보만 사용 가능",
            "NO_RUNWAYS_AVAILABLE": "사용 가능한 활주로 없음"
        }
        
        print(f"[ResponseProcessor] Confluence 문서 기준 응답 테이블 로드 완료 ({len(self.standard_responses)}개)")
        
    def _convert_aviation_numbers(self, text: str) -> str:
        """
        항공 통신 표준에 맞게 숫자를 변환
        예: "123" → "one two three"
        """
        # 숫자를 개별 자릿수로 변환하는 매핑
        number_map = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        
        # 연속된 숫자를 찾아서 변환
        def replace_numbers(match):
            number = match.group()
            return ' '.join([number_map[digit] for digit in number])
        
        # 2자리 이상의 숫자를 개별 자릿수로 변환
        text = re.sub(r'\b\d{2,}\b', replace_numbers, text)
        
        return text
    
    def process_response(self, response_data: Dict[str, Any], original_request: Dict[str, Any]) -> Tuple[bool, str]:
        """
        메인 서버 응답을 처리하여 표준 자연어 응답 생성 (Confluence 문서 기준)
        
        Args:
            response_data: 메인 서버 응답 데이터 (Confluence 문서 형식)
            original_request: 원본 요청 정보 (콜사인 등)
            
        Returns:
            (성공 여부, 자연어 응답 텍스트) 튜플
        """
        try:
            # 1. 기본 정보 추출
            callsign = original_request.get("callsign", "Aircraft")
            intent = response_data.get("intent", "unknown")
            
            print(f"[ResponseProcessor] 🆔 원본 콜사인: '{callsign}'")
            print(f"[ResponseProcessor] 📋 전체 original_request: {original_request}")
            
            # 2. Confluence 문서 기준 오류 응답 처리
            if response_data.get("status") == "error":
                response_code = response_data.get("response_code", "UNRECOGNIZED_COMMAND")
                return self._generate_standard_response(response_code, callsign, {})
            
            # 3. Confluence 문서 기준 정상 응답 처리
            if response_data.get("type") == "response" and response_data.get("status") == "success":
                response_code = response_data.get("response_code", "UNRECOGNIZED_COMMAND")
                
                print(f"[ResponseProcessor] 🎯 Confluence 표준 응답 처리: {intent} - {response_code}")
                print(f"[ResponseProcessor] 📝 응답 설명: {self.response_descriptions.get(response_code, '알 수 없음')}")
                
                # 표준 응답 텍스트 생성
                return self._generate_standard_response(response_code, callsign, {})
            
            else:
                # 예상하지 못한 응답 형식
                print(f"[ResponseProcessor] ⚠️ 예상하지 못한 응답 형식: {response_data}")
                return self._generate_standard_response("UNRECOGNIZED_COMMAND", callsign, {})
                
        except Exception as e:
            print(f"[ResponseProcessor] ❌ 응답 처리 오류: {e}")
            callsign = original_request.get("callsign", "Aircraft")
            return self._generate_standard_response("TIMEOUT", callsign, {})
    
    def _generate_standard_response(self, response_code: str, callsign: str, result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Confluence 문서 기준 표준 응답 코드를 사용하여 자연어 응답 생성
        
        Args:
            response_code: 표준 응답 코드 (Confluence 문서 기준)
            callsign: 항공기 콜사인
            result: 추가 데이터 (현재 사용하지 않음)
            
        Returns:
            (성공 여부, 자연어 응답 텍스트) 튜플
        """
        # 표준 응답 텍스트 조회
        if response_code in self.standard_responses:
            base_response = self.standard_responses[response_code]
            success = True
        else:
            print(f"[ResponseProcessor] ⚠️ 알 수 없는 응답 코드: {response_code}")
            base_response = self.standard_responses["UNRECOGNIZED_COMMAND"]
            success = False
        
        # 콜사인과 함께 최종 응답 생성
        if callsign and callsign != "Aircraft":
            final_response = f"{callsign}, {base_response}"
        else:
            final_response = base_response
        
        # 항공 통신 표준에 맞게 숫자 변환 (123 → one two three)
        final_response = self._convert_aviation_numbers(final_response)
        
        print(f"[ResponseProcessor] ✅ 최종 응답: '{final_response}'")
        return success, final_response
    
    def _handle_error_response(self, response_data: Dict[str, Any], callsign: str) -> Tuple[bool, str]:
        """오류 응답 처리 - Confluence 문서 기준"""
        error_type = response_data.get("error", "unknown")
        
        # 오류 타입을 표준 응답 코드로 매핑
        error_mapping = {
            "timeout": "TIMEOUT",
            "connection_failed": "NO_DATA_AVAILABLE", 
            "unknown_intent": "UNRECOGNIZED_COMMAND",
            "invalid_area": "INVALID_AREA",
            "partial_data": "PARTIAL_RESPONSE"
        }
        
        response_code = error_mapping.get(error_type, "UNRECOGNIZED_COMMAND")
        print(f"[ResponseProcessor] 🚨 오류 응답: {error_type} → {response_code}")
        
        return self._generate_standard_response(response_code, callsign, {})
    
    def create_tts_request(self, response_text: str, session_id: str) -> Dict[str, Any]:
        """
        TTS 요청 페이로드 생성
        
        Args:
            response_text: 음성으로 변환할 텍스트
            session_id: 세션 ID
            
        Returns:
            TTS 요청 페이로드
        """
        tts_request = {
            "type": "command",
            "command": "synthesize_speech",
            "text": response_text,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "voice_settings": {
                "language": "en",
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 0.8
            }
        }
        
        print(f"[ResponseProcessor] TTS 요청 생성: '{response_text[:50]}...'")
        return tts_request
    
    def validate_response_data(self, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Confluence 문서 기준 응답 데이터 유효성 검증
        
        Args:
            response_data: 검증할 응답 데이터
            
        Returns:
            (유효성, 오류 메시지) 튜플
        """
        # 1. 기본 구조 확인
        if not isinstance(response_data, dict):
            return False, "응답 데이터가 딕셔너리가 아닙니다"
        
        # 2. 필수 필드 확인
        if "type" not in response_data:
            return False, "응답 타입이 없습니다"
        
        if "status" not in response_data:
            return False, "상태 필드가 없습니다"
        
        # 3. 오류 응답인 경우
        if response_data.get("status") == "error":
            if "response_code" not in response_data:
                return False, "오류 응답 코드가 없습니다"
            return True, "오류 응답 (정상 처리 가능)"
        
        # 4. 정상 응답인 경우
        if response_data.get("type") == "response" and response_data.get("status") == "success":
            if "response_code" not in response_data:
                return False, "응답 코드가 없습니다"
            
            if "intent" not in response_data:
                return False, "인텐트가 없습니다"
        
        return True, "유효한 응답 데이터"
    
    def get_response_summary(self, response_data: Dict[str, Any]) -> str:
        """
        응답 데이터 요약 정보 반환 (Confluence 문서 기준)
        
        Args:
            response_data: 응답 데이터
            
        Returns:
            요약 문자열
        """
        if response_data.get("status") == "error":
            return f"오류: {response_data.get('response_code', 'unknown')}"
        
        if response_data.get("type") == "response" and response_data.get("status") == "success":
            intent = response_data.get("intent", "unknown")
            response_code = response_data.get("response_code", "unknown")
            
            return f"{intent}: {response_code}"
        
        return "알 수 없는 응답 형식"
    