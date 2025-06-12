from .pyttsx3_engine import TTSEngine
from .coqui_tts_engine import CoquiTTSEngine
from typing import Optional

class HybridTTSEngine:
    def __init__(self, 
                 use_coqui: bool = True,
                 coqui_model: str = "tts_models/en/ljspeech/glow-tts",
                 fallback_to_pyttsx3: bool = True):
        """
        하이브리드 TTS 엔진 - Coqui TTS 우선, pyttsx3 fallback
        
        Args:
            use_coqui: Coqui TTS 사용 여부
            coqui_model: Coqui TTS 모델명 (기본: glow-tts - 더 안정적)
            fallback_to_pyttsx3: Coqui 실패시 pyttsx3 사용 여부
        """
        self.use_coqui = use_coqui
        self.fallback_to_pyttsx3 = fallback_to_pyttsx3
        
        # pyttsx3 엔진 (항상 준비)
        print("[HybridTTS] pyttsx3 엔진 초기화 중...")
        self.pyttsx3_engine = TTSEngine()
        
        # Coqui TTS 엔진 (옵션)
        self.coqui_engine: Optional[CoquiTTSEngine] = None
        self.coqui_failed = False  # 🆕 Coqui 실패 플래그
        
        if use_coqui:
            try:
                print("[HybridTTS] 개선된 Coqui TTS 엔진 초기화 중...")
                self.coqui_engine = CoquiTTSEngine(model_name=coqui_model)
                if not self.coqui_engine.is_engine_ready():
                    print("[HybridTTS] ⚠️ Coqui TTS 엔진이 준비되지 않음 - pyttsx3 사용")
                    self.coqui_failed = True
                else:
                    print("[HybridTTS] ✅ Coqui TTS 엔진 준비 완료")
            except Exception as e:
                print(f"[HybridTTS] Coqui TTS 초기화 실패: {e}")
                self.coqui_failed = True
                if not fallback_to_pyttsx3:
                    raise
        else:
            print("[HybridTTS] Coqui TTS 비활성화 - pyttsx3만 사용")
    
    def speak(self, text: str, blocking: bool = True, 
              force_pyttsx3: bool = False, language: str = "en"):
        """
        텍스트 음성 변환
        
        Args:
            text: 변환할 텍스트
            blocking: 동기/비동기 처리
            force_pyttsx3: pyttsx3 강제 사용
            language: 언어 (Coqui용)
        """
        # 🆕 음소거 상태 확인
        current_volume = self.get_current_volume()
        if current_volume == 0.0:
            print(f"[HybridTTS] 🔇 음소거 상태 - 음성 재생 생략: '{text}'")
            return
        
        # 🆕 Coqui 실패했거나 강제 pyttsx3 사용
        if force_pyttsx3 or self.coqui_failed or not self.coqui_engine or not self.coqui_engine.is_engine_ready():
            print("[HybridTTS] pyttsx3 사용")
            return self.pyttsx3_engine.speak(text, blocking)
        
        # Coqui TTS 시도
        try:
            print("[HybridTTS] Coqui TTS 시도...")
            return self.coqui_engine.speak(text, blocking, language)
        except Exception as e:
            print(f"[HybridTTS] Coqui TTS 실패: {e}")
            self.coqui_failed = True  # 🆕 실패 플래그 설정
            
            # Fallback to pyttsx3
            if self.fallback_to_pyttsx3:
                print("[HybridTTS] pyttsx3로 fallback")
                return self.pyttsx3_engine.speak(text, blocking)
            else:
                raise
    
    def speak_async(self, text: str, force_pyttsx3: bool = False, language: str = "en"):
        """비동기 음성 재생"""
        self.speak(text, blocking=False, force_pyttsx3=force_pyttsx3, language=language)
    
    def stop_speaking(self):
        """음성 재생 중지"""
        if self.coqui_engine:
            self.coqui_engine.stop_speaking()
        self.pyttsx3_engine.stop_speaking()
    
    def set_rate(self, rate: int):
        """속도 설정"""
        self.pyttsx3_engine.set_rate(rate)
        if self.coqui_engine:
            self.coqui_engine.set_rate(rate)
    
    def set_volume(self, volume: float):
        """음량 설정"""
        print(f"[HybridTTS] 볼륨 설정: {volume}")
        self.pyttsx3_engine.set_volume(volume)
        if self.coqui_engine:
            self.coqui_engine.set_volume(volume)
    
    def is_engine_ready(self) -> bool:
        """엔진 준비 상태"""
        return (self.coqui_engine and self.coqui_engine.is_engine_ready()) or \
               self.pyttsx3_engine.is_engine_ready()
    
    def get_current_engine(self) -> str:
        """현재 사용 중인 엔진"""
        if self.coqui_engine and self.coqui_engine.is_engine_ready() and self.use_coqui and not self.coqui_failed:
            return "Coqui TTS"
        return "pyttsx3"
    
    def toggle_engine(self):
        """엔진 전환"""
        self.use_coqui = not self.use_coqui
        print(f"[HybridTTS] 엔진 전환: {self.get_current_engine()}")
        
    def get_status(self) -> dict:
        """현재 상태 정보"""
        return {
            "current_engine": self.get_current_engine(),
            "coqui_available": self.coqui_engine is not None and self.coqui_engine.is_engine_ready(),
            "pyttsx3_available": self.pyttsx3_engine.is_engine_ready(),
            "use_coqui": self.use_coqui,
            "fallback_enabled": self.fallback_to_pyttsx3
        }
    
    def get_current_volume(self) -> float:
        """🆕 현재 볼륨 반환"""
        if self.coqui_engine and self.coqui_engine.is_engine_ready() and self.use_coqui:
            return self.coqui_engine.volume
        return self.pyttsx3_engine.volume 