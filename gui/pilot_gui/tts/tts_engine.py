import pyttsx3
import io
import wave
import threading
import time
from typing import Optional

class TTSEngine:
    def __init__(self, rate: int = 150, volume: float = 0.9, voice_index: int = 0):
        """
        TTS 엔진 초기화
        
        Args:
            rate: 말하기 속도 (words per minute)
            volume: 음량 (0.0 ~ 1.0)
            voice_index: 음성 인덱스 (0: 기본, 1: 대체 음성)
        """
        self.rate = rate
        self.volume = volume
        self.voice_index = voice_index
        self.engine = None
        self.is_speaking = False
        self._init_engine()
    
    def _init_engine(self):
        """
        pyttsx3 엔진 초기화
        """
        try:
            self.engine = pyttsx3.init()
            
            # 음성 속도 설정
            self.engine.setProperty('rate', self.rate)
            
            # 음량 설정
            self.engine.setProperty('volume', self.volume)
            
            # 사용 가능한 음성 확인 및 설정
            voices = self.engine.getProperty('voices')
            if voices and len(voices) > self.voice_index:
                self.engine.setProperty('voice', voices[self.voice_index].id)
                print(f"[TTSEngine] 음성 설정: {voices[self.voice_index].name}")
            
            print(f"[TTSEngine] TTS 엔진 초기화 완료 (속도: {self.rate}, 음량: {self.volume})")
            
        except Exception as e:
            print(f"[TTSEngine] TTS 엔진 초기화 실패: {e}")
            self.engine = None
    
    def speak(self, text: str, blocking: bool = True):
        """
        텍스트를 음성으로 변환해 스피커 출력
        
        Args:
            text: 변환할 텍스트
            blocking: True면 음성 재생 완료까지 대기, False면 비동기 재생
        """
        if not self.engine:
            print(f"[TTSEngine] 엔진이 초기화되지 않음. 텍스트 출력: {text}")
            return
        
        if not text or not text.strip():
            print("[TTSEngine] 빈 텍스트는 음성 변환할 수 없습니다.")
            return
        
        try:
            print(f"[TTSEngine] 음성 변환 시작: '{text}'")
            self.is_speaking = True
            
            if blocking:
                # 동기 방식 - 재생 완료까지 대기
                self.engine.say(text)
                self.engine.runAndWait()
                self.is_speaking = False
                print("[TTSEngine] 음성 재생 완료")
            else:
                # 비동기 방식 - 별도 스레드에서 재생
                def speak_async():
                    self.engine.say(text)
                    self.engine.runAndWait()
                    self.is_speaking = False
                    print("[TTSEngine] 음성 재생 완료 (비동기)")
                
                thread = threading.Thread(target=speak_async)
                thread.daemon = True
                thread.start()
                
        except Exception as e:
            print(f"[TTSEngine] 음성 변환 오류: {e}")
            self.is_speaking = False
    
    def speak_async(self, text: str):
        """
        비동기 음성 재생 (편의 메서드)
        """
        self.speak(text, blocking=False)
    
    def stop_speaking(self):
        """
        현재 음성 재생 중지
        """
        if self.engine and self.is_speaking:
            try:
                self.engine.stop()
                self.is_speaking = False
                print("[TTSEngine] 음성 재생 중지")
            except Exception as e:
                print(f"[TTSEngine] 음성 재생 중지 오류: {e}")
    
    def set_rate(self, rate: int):
        """
        말하기 속도 변경
        
        Args:
            rate: 새로운 속도 (words per minute)
        """
        if self.engine:
            try:
                self.rate = rate
                self.engine.setProperty('rate', rate)
                print(f"[TTSEngine] 말하기 속도 변경: {rate}")
            except Exception as e:
                print(f"[TTSEngine] 속도 변경 오류: {e}")
    
    def set_volume(self, volume: float):
        """
        음량 변경
        
        Args:
            volume: 새로운 음량 (0.0 ~ 1.0)
        """
        if self.engine:
            try:
                self.volume = max(0.0, min(1.0, volume))  # 0.0 ~ 1.0 범위로 제한
                self.engine.setProperty('volume', self.volume)
                print(f"[TTSEngine] 음량 변경: {self.volume}")
            except Exception as e:
                print(f"[TTSEngine] 음량 변경 오류: {e}")
    
    def set_voice(self, voice_index: int):
        """
        음성 변경
        
        Args:
            voice_index: 음성 인덱스
        """
        if self.engine:
            try:
                voices = self.engine.getProperty('voices')
                if voices and 0 <= voice_index < len(voices):
                    self.voice_index = voice_index
                    self.engine.setProperty('voice', voices[voice_index].id)
                    print(f"[TTSEngine] 음성 변경: {voices[voice_index].name}")
                else:
                    print(f"[TTSEngine] 잘못된 음성 인덱스: {voice_index}")
            except Exception as e:
                print(f"[TTSEngine] 음성 변경 오류: {e}")
    
    def get_available_voices(self) -> list:
        """
        사용 가능한 음성 목록 반환
        """
        if self.engine:
            try:
                voices = self.engine.getProperty('voices')
                return [(i, voice.name, voice.id) for i, voice in enumerate(voices)]
            except Exception as e:
                print(f"[TTSEngine] 음성 목록 조회 오류: {e}")
        return []
    
    def is_engine_ready(self) -> bool:
        """
        TTS 엔진 준비 상태 확인
        """
        return self.engine is not None
    
    def get_current_settings(self) -> dict:
        """
        현재 TTS 설정 반환
        """
        return {
            "rate": self.rate,
            "volume": self.volume,
            "voice_index": self.voice_index,
            "is_speaking": self.is_speaking,
            "engine_ready": self.is_engine_ready()
        }
    
    def __del__(self):
        """
        소멸자 - 엔진 정리
        """
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
