from typing import Dict, Any, Optional
from datetime import datetime

class EventTTS:
    """
    이벤트 TTS 처리
    
    이벤트 발생 시 적절한 TTS 메시지를 생성하고 재생합니다.
    """
    
    def __init__(self, tts_engine=None):
        """
        이벤트 TTS 초기화
        
        Args:
            tts_engine: TTS 엔진 인스턴스
        """
        self.tts_engine = tts_engine
        
        # 이벤트별 TTS 메시지 템플릿
        self.tts_templates = {
            "bird_risk": {
                "HIGH": "Bird strike risk level high. Exercise extreme caution.",
                "MEDIUM": "Bird strike risk level medium. Maintain awareness.",
                "LOW": "Bird strike risk level low. Normal operations."
            },
            "runway_alpha": {
                "WARNING": "Runway Alpha warning. Check runway conditions.",
                "CLEAR": "Runway Alpha clear for operations."
            },
            "runway_bravo": {
                "WARNING": "Runway Bravo warning. Check runway conditions.",
                "CLEAR": "Runway Bravo clear for operations."
            }
        }
        
        # 한국어 TTS 메시지 템플릿 (필요시 사용)
        self.tts_templates_ko = {
            "bird_risk": {
                "HIGH": "조류 충돌 위험도 높음. 극도로 주의하시기 바랍니다.",
                "MEDIUM": "조류 충돌 위험도 보통. 주의를 유지하시기 바랍니다.",
                "LOW": "조류 충돌 위험도 낮음. 정상 운항 가능합니다."
            },
            "runway_alpha": {
                "WARNING": "활주로 알파 경고. 활주로 상태를 확인하시기 바랍니다.",
                "CLEAR": "활주로 알파 운항 가능합니다."
            },
            "runway_bravo": {
                "WARNING": "활주로 브라보 경고. 활주로 상태를 확인하시기 바랍니다.",
                "CLEAR": "활주로 브라보 운항 가능합니다."
            }
        }
        
        print("[EventTTS] 초기화 완료")
    
    def set_tts_engine(self, tts_engine):
        """
        TTS 엔진 설정
        
        Args:
            tts_engine: TTS 엔진 인스턴스
        """
        self.tts_engine = tts_engine
        print("[EventTTS] TTS 엔진 설정 완료")
    
    def play_event_notification(self, event_type: str, result: str, language: str = "en"):
        """
        이벤트 TTS 알림 재생
        
        Args:
            event_type: 이벤트 타입 (bird_risk, runway_alpha, runway_bravo)
            result: 결과 값 (HIGH, MEDIUM, LOW, WARNING, CLEAR)
            language: 언어 ("en" 또는 "ko")
        """
        if not self.tts_engine:
            print("[EventTTS] ⚠️ TTS 엔진이 설정되지 않음")
            return
        
        try:
            # TTS 메시지 생성
            tts_message = self.get_tts_message(event_type, result, language)
            
            if not tts_message:
                print(f"[EventTTS] ⚠️ TTS 메시지를 찾을 수 없음: {event_type} - {result}")
                return
            
            # TTS 엔진의 speak_event 메서드 사용 (충돌 방지)
            if hasattr(self.tts_engine, 'speak_event'):
                self.tts_engine.speak_event(tts_message, language=language)
                print(f"[EventTTS] ✅ 이벤트 TTS 재생: {event_type} - {result}")
            else:
                # 일반 speak 메서드 사용 (폴백)
                self.tts_engine.speak(tts_message, tts_type="event", language=language)
                print(f"[EventTTS] ✅ 이벤트 TTS 재생 (폴백): {event_type} - {result}")
                
        except Exception as e:
            print(f"[EventTTS] ❌ TTS 재생 오류: {e}")
    
    def get_tts_message(self, event_type: str, result: str, language: str = "en") -> Optional[str]:
        """
        TTS 메시지 생성
        
        Args:
            event_type: 이벤트 타입
            result: 결과 값
            language: 언어
            
        Returns:
            TTS 메시지 문자열
        """
        templates = self.tts_templates_ko if language == "ko" else self.tts_templates
        
        return templates.get(event_type, {}).get(result)
    
    def get_priority_delay(self, event_type: str, result: str) -> float:
        """
        이벤트 우선순위에 따른 지연 시간 계산
        
        Args:
            event_type: 이벤트 타입
            result: 결과 값
            
        Returns:
            지연 시간 (초)
        """
        # 높은 우선순위 이벤트는 즉시 재생
        high_priority = {
            "bird_risk": ["HIGH"],
            "runway_alpha": ["WARNING"],
            "runway_bravo": ["WARNING"]
        }
        
        if result in high_priority.get(event_type, []):
            return 0.0  # 즉시 재생
        else:
            return 0.5  # 0.5초 지연
    
    def format_event_for_log(self, event_type: str, result: str, language: str = "en") -> str:
        """
        로그용 이벤트 포맷팅
        
        Args:
            event_type: 이벤트 타입
            result: 결과 값
            language: 언어
            
        Returns:
            로그용 문자열
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        tts_message = self.get_tts_message(event_type, result, language)
        
        return f"[{timestamp}] 🔔 EVENT: {tts_message}"
    
    def should_interrupt_current_tts(self, event_type: str, result: str) -> bool:
        """
        현재 TTS를 중단하고 이벤트 TTS를 재생할지 결정
        
        Args:
            event_type: 이벤트 타입
            result: 결과 값
            
        Returns:
            중단 여부
        """
        # 높은 우선순위 이벤트는 현재 TTS를 중단
        interrupt_events = {
            "bird_risk": ["HIGH"],
            "runway_alpha": ["WARNING"],
            "runway_bravo": ["WARNING"]
        }
        
        return result in interrupt_events.get(event_type, [])
    
    def get_available_languages(self) -> list:
        """
        지원하는 언어 목록 반환
        
        Returns:
            지원하는 언어 코드 리스트
        """
        return ["en", "ko"]
    
    def get_event_types(self) -> list:
        """
        지원하는 이벤트 타입 목록 반환
        
        Returns:
            지원하는 이벤트 타입 리스트
        """
        return list(self.tts_templates.keys())
    
    def add_custom_template(self, event_type: str, result: str, message: str, language: str = "en"):
        """
        사용자 정의 TTS 템플릿 추가
        
        Args:
            event_type: 이벤트 타입
            result: 결과 값
            message: TTS 메시지
            language: 언어
        """
        templates = self.tts_templates_ko if language == "ko" else self.tts_templates
        
        if event_type not in templates:
            templates[event_type] = {}
        
        templates[event_type][result] = message
        print(f"[EventTTS] 사용자 정의 템플릿 추가: {event_type} - {result} ({language})") 