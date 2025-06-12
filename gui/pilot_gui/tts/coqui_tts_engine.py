import torch
import io
import wave
import threading
import time
import tempfile
import os
import numpy as np
from typing import Optional, List
from TTS.api import TTS

class CoquiTTSEngine:
    def __init__(self, 
                 model_name: str = "tts_models/en/ljspeech/glow-tts",
                 rate: int = 150, 
                 volume: float = 0.9,
                 device: str = "auto"):
        """
        새로운 Coqui TTS 엔진 초기화 (음성 품질 개선)
        
        Args:
            model_name: 사용할 TTS 모델명 (기본: glow-tts - 더 안정적)
            rate: 말하기 속도 (사용 안함 - Coqui는 자체 속도)
            volume: 음량 (0.0 ~ 1.0)
            device: 계산 장치 ("auto", "cuda", "cpu")
        """
        self.model_name = model_name
        self.rate = rate  # 호환성 유지용
        self.volume = volume
        self.device = self._get_device(device)
        self.tts = None
        self.is_speaking = False
        self.is_loading = False
        self._init_engine()
    
    def _get_device(self, device: str) -> str:
        """최적 장치 선택"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _init_engine(self):
        """새로운 Coqui TTS 엔진 초기화 (안정적인 모델 우선)"""
        try:
            print(f"[CoquiTTS] 🚀 TTS 모델 로딩: {self.model_name}")
            print(f"[CoquiTTS] 🔧 장치: {self.device}")
            self.is_loading = True
            
            # 새로운 TTS API 초기화 (Python 3.12 호환) - 프로그레스바 활성화
            self.tts = TTS(self.model_name, progress_bar=True).to(self.device)
            
            print(f"[CoquiTTS] ✅ TTS 엔진 초기화 완료")
            
            # 모델 정보 출력
            if hasattr(self.tts, 'synthesizer') and hasattr(self.tts.synthesizer, 'tts_model'):
                model_info = self.tts.synthesizer.tts_model
                print(f"[CoquiTTS] 📊 모델 정보: {type(model_info).__name__}")
            
            # 언어 정보 (있는 경우)
            if hasattr(self.tts, 'languages') and self.tts.languages:
                print(f"[CoquiTTS] 🌍 지원 언어: {self.tts.languages}")
            
            # 스피커 정보 (있는 경우)
            if hasattr(self.tts, 'speakers') and self.tts.speakers:
                print(f"[CoquiTTS] 🎤 스피커 수: {len(self.tts.speakers)}")
            
            self.is_loading = False
            
        except Exception as e:
            print(f"[CoquiTTS] ❌ TTS 엔진 초기화 실패: {e}")
            print(f"[CoquiTTS] 💡 안정적인 대안 모델로 재시도...")
            
            # 🆕 안정적인 모델 우선순위로 변경 (glow-tts > speedy-speech > tacotron2)
            fallback_models = [
                "tts_models/en/ljspeech/glow-tts",        # 가장 안정적
                "tts_models/en/ljspeech/speedy-speech",   # 빠르고 안정적
                "tts_models/en/ljspeech/tacotron2-DDC"    # 마지막 옵션
            ]
            
            for fallback_model in fallback_models:
                if fallback_model != self.model_name:
                    try:
                        print(f"[CoquiTTS] 🔄 대안 모델 시도: {fallback_model}")
                        self.tts = TTS(fallback_model, progress_bar=True).to(self.device)
                        self.model_name = fallback_model
                        print(f"[CoquiTTS] ✅ 대안 모델 로딩 성공!")
                        break
                    except Exception as fallback_error:
                        print(f"[CoquiTTS] ❌ 대안 모델 실패: {fallback_error}")
                        continue
            
            if not self.tts:
                print(f"[CoquiTTS] ❌ 모든 모델 로딩 실패")
            
            self.is_loading = False
    
    def speak(self, text: str, blocking: bool = True, language: str = "en"):
        """
        텍스트를 음성으로 변환해 스피커 출력
        
        Args:
            text: 변환할 텍스트
            blocking: True면 음성 재생 완료까지 대기
            language: 언어 코드
        """
        if self.is_loading:
            print("[CoquiTTS] 모델 로딩 중... 잠시 후 다시 시도하세요.")
            return
        
        if not self.tts:
            print(f"[CoquiTTS] 엔진이 초기화되지 않음. 텍스트 출력: {text}")
            return
        
        if not text or not text.strip():
            print("[CoquiTTS] 빈 텍스트는 음성 변환할 수 없습니다.")
            return
        
        try:
            print(f"[CoquiTTS] 음성 변환 시작: '{text}'")
            self.is_speaking = True
            
            if blocking:
                self._generate_and_play(text, language)
                self.is_speaking = False
                print("[CoquiTTS] 음성 재생 완료")
            else:
                # 비동기 방식
                def speak_async():
                    self._generate_and_play(text, language)
                    self.is_speaking = False
                    print("[CoquiTTS] 음성 재생 완료 (비동기)")
                
                thread = threading.Thread(target=speak_async)
                thread.daemon = True
                thread.start()
                
        except Exception as e:
            print(f"[CoquiTTS] 음성 변환 오류: {e}")
            self.is_speaking = False
    
    def _generate_and_play(self, text: str, language: str = "en"):
        """🆕 텍스트를 음성으로 변환하고 재생 (볼륨 적용)"""
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 🆕 텍스트 전처리 (항공 용어 처리)
            processed_text = self._preprocess_text(text)
            
            # TTS 생성 - 다중 언어 지원
            print(f"[CoquiTTS] 🎵 음성 생성 중... (언어: {language})")
            
            if hasattr(self.tts, 'languages') and self.tts.languages and language in self.tts.languages:
                # 다중 언어 모델
                self.tts.tts_to_file(text=processed_text, file_path=temp_path, language=language)
            else:
                # 단일 언어 모델
                self.tts.tts_to_file(text=processed_text, file_path=temp_path)
            
            # 🆕 볼륨 적용
            if self.volume != 1.0:
                self._apply_volume_to_file(temp_path)
            
            # 오디오 재생
            self._play_audio_file_improved(temp_path)
            
            # 임시 파일 정리
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception as e:
            print(f"[CoquiTTS] 음성 생성 및 재생 오류: {e}")
            raise
    
    def _apply_volume_to_file(self, file_path: str):
        """🆕 WAV 파일에 볼륨 적용"""
        try:
            # WAV 파일 읽기
            import wave
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
            
            # numpy 배열로 변환
            if sample_width == 2:  # 16-bit
                audio_data = np.frombuffer(frames, dtype=np.int16)
            elif sample_width == 4:  # 32-bit
                audio_data = np.frombuffer(frames, dtype=np.int32)
            else:
                print(f"[CoquiTTS] ⚠️ 지원하지 않는 샘플 폭: {sample_width}")
                return
            
            # 볼륨 적용
            modified_audio = self._apply_audio_volume(audio_data)
            
            # WAV 파일로 다시 저장
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(modified_audio.tobytes())
            
            print(f"[CoquiTTS] ✅ 볼륨 적용 완료: {self.volume:.2f}")
            
        except Exception as e:
            print(f"[CoquiTTS] ❌ 볼륨 적용 오류: {e}")
    
    def _preprocess_text(self, text: str) -> str:
        """
        🆕 TTS 품질 개선을 위한 텍스트 전처리 - 이상한 소리 방지
        """
        # 기본 정리
        processed = text.strip()
        
        # 연속된 공백 제거
        import re
        processed = re.sub(r'\s+', ' ', processed)
        
        # 🆕 특수 문자 정리 (TTS 아티팩트 방지)
        processed = re.sub(r'[^\w\s\.,!?-]', '', processed)  # 알파벳, 숫자, 기본 구두점만 유지
        
        # 🆕 연속된 구두점 제거
        processed = re.sub(r'[.]{2,}', '.', processed)  # 연속된 마침표
        processed = re.sub(r'[,]{2,}', ',', processed)  # 연속된 쉼표
        
        # 🆕 숫자 뒤 공백 정리 (항공 통신 최적화)
        processed = re.sub(r'(\d)\s+(\d)', r'\1 \2', processed)  # 숫자 사이 공백 정규화
        
        # 🆕 문장 끝 정리 (자연스러운 종료를 위해)
        if processed and not processed.endswith(('.', '!', '?')):
            processed += '.'
        
        # 🆕 끝부분 공백 완전 제거
        processed = processed.rstrip()
        
        print(f"[CoquiTTS] 텍스트 전처리: '{text}' → '{processed}'")
        return processed
    
    def _postprocess_audio(self, audio_path: str) -> str:
        """
        🆕 오디오 후처리 (무음 제거, 품질 개선) - 이상한 소리 방지 개선
        """
        try:
            import scipy.io.wavfile as wavfile
            
            # WAV 파일 읽기
            sample_rate, audio_data = wavfile.read(audio_path)
            
            # 스테레오를 모노로 변환 (필요한 경우)
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # 정규화
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if np.max(np.abs(audio_data)) > 1.0:
                    audio_data = audio_data / np.max(np.abs(audio_data))
            
            # 🆕 더 보수적인 무음 제거 (실제 음성 끝부분 보호)
            audio_data = self._trim_silence_conservative(audio_data, threshold=0.005)  # 더 낮은 임계값
            
            # 🆕 더 부드러운 페이드아웃 (이상한 소리 방지)
            audio_data = self._apply_smooth_fadeout(audio_data, fade_duration=0.05)  # 0.05초로 단축
            
            # 🆕 끝부분에 짧은 무음 추가 (완전한 종료 보장)
            silence_samples = int(sample_rate * 0.02)  # 0.02초 무음
            silence = np.zeros(silence_samples, dtype=np.float32)
            audio_data = np.concatenate([audio_data, silence])
            
            # 후처리된 파일 저장
            processed_path = audio_path.replace('.wav', '_processed.wav')
            wavfile.write(processed_path, sample_rate, audio_data)
            
            print(f"[CoquiTTS] 🔧 오디오 후처리 완료 (보수적 무음 제거, 부드러운 페이드아웃)")
            return processed_path
            
        except Exception as e:
            print(f"[CoquiTTS] ⚠️ 오디오 후처리 실패, 원본 사용: {e}")
            return audio_path
    
    def _trim_silence_conservative(self, audio_data: np.ndarray, threshold: float = 0.005) -> np.ndarray:
        """
        🆕 보수적인 무음 구간 제거 (실제 음성 끝부분 보호)
        """
        # 절대값이 임계값보다 큰 구간 찾기
        non_silent = np.abs(audio_data) > threshold
        
        if not np.any(non_silent):
            return audio_data  # 모든 구간이 무음인 경우 원본 반환
        
        # 첫 번째와 마지막 소리 구간 찾기
        first_sound = np.argmax(non_silent)
        last_sound = len(non_silent) - 1 - np.argmax(non_silent[::-1])
        
        # 🆕 더 넉넉한 여유 공간 (음성 끝부분 보호)
        margin = int(len(audio_data) * 0.05)  # 5% 여유 (기존 2%에서 증가)
        start = max(0, first_sound - margin)
        end = min(len(audio_data), last_sound + margin)
        
        return audio_data[start:end]
    
    def _apply_smooth_fadeout(self, audio_data: np.ndarray, fade_duration: float = 0.05) -> np.ndarray:
        """
        🆕 부드러운 페이드아웃 적용 (이상한 소리 방지)
        """
        fade_samples = int(len(audio_data) * fade_duration / 2.0)  # 전체 길이 대비 비율로 계산
        fade_samples = min(fade_samples, len(audio_data) // 4)  # 최대 25%까지만
        
        if len(audio_data) <= fade_samples or fade_samples <= 0:
            return audio_data
        
        # 🆕 더 부드러운 페이드아웃 곡선 (지수 함수 사용)
        fade_curve = np.exp(-np.linspace(0, 3, fade_samples))  # 지수적 감소
        
        # 끝부분에 페이드아웃 적용
        audio_data[-fade_samples:] *= fade_curve
        
        return audio_data
    
    def _play_audio_file_improved(self, file_path: str):
        """🆕 개선된 오디오 파일 재생 (이상한 소리 방지)"""
        import platform
        import subprocess
        
        system = platform.system()
        try:
            if system == "Linux":
                # 🆕 aplay 옵션 개선 (더 큰 버퍼, 안정적 재생)
                subprocess.run([
                    "aplay", 
                    "--buffer-size=8192",   # 버퍼 크기 증가 (4096 → 8192)
                    "--period-size=2048",   # 주기 크기 증가 (1024 → 2048)
                    "--quiet",              # 불필요한 출력 제거
                    file_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            elif system == "Windows":
                # Windows에서 powershell 사용
                subprocess.run([
                    "powershell", "-c", 
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"
                ], check=True)
                
            elif system == "Darwin":  # macOS
                subprocess.run(["afplay", file_path], check=True)
                
            else:
                print(f"[CoquiTTS] 지원하지 않는 운영체제: {system}")
                
        except subprocess.CalledProcessError as e:
            print(f"[CoquiTTS] 오디오 재생 오류: {e}")
            # 🆕 fallback: 더 안전한 기본 aplay 시도
            try:
                subprocess.run([
                    "aplay", 
                    "--quiet",  # 조용한 모드
                    file_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                print(f"[CoquiTTS] 기본 재생도 실패")
                
        except FileNotFoundError:
            print(f"[CoquiTTS] 오디오 재생 프로그램을 찾을 수 없습니다.")
    
    def speak_async(self, text: str, language: str = "en"):
        """비동기 음성 재생"""
        self.speak(text, blocking=False, language=language)
    
    def stop_speaking(self):
        """현재 음성 재생 중지"""
        # Coqui TTS는 파일 기반이므로 프로세스 중지가 복잡
        # 현재는 플래그만 설정
        self.is_speaking = False
        print("[CoquiTTS] 음성 재생 중지 요청")
    
    def set_rate(self, rate: int):
        """속도 설정 (Coqui TTS에서는 미지원)"""
        self.rate = rate
        print(f"[CoquiTTS] 속도 설정 요청: {rate} (Coqui TTS는 속도 조절 미지원)")
    
    def set_volume(self, volume: float):
        """음량 설정"""
        self.volume = max(0.0, min(1.0, volume))
        print(f"[CoquiTTS] 음량 설정: {self.volume}")
        
        # 🆕 실시간 시스템 볼륨 조절 추가
        self._apply_system_volume()
    
    def _apply_system_volume(self):
        """🆕 시스템 볼륨에 반영"""
        try:
            import subprocess
            import platform
            
            # 볼륨을 0-100% 범위로 변환
            volume_percent = int(self.volume * 100)
            
            system = platform.system()
            if system == "Linux":
                # PulseAudio 볼륨 조절 (가장 일반적)
                try:
                    subprocess.run([
                        "pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume_percent}%"
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"[CoquiTTS] ✅ PulseAudio 볼륨 설정: {volume_percent}%")
                    return
                except:
                    pass
                
                # ALSA 볼륨 조절 (fallback)
                try:
                    subprocess.run([
                        "amixer", "set", "Master", f"{volume_percent}%"
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"[CoquiTTS] ✅ ALSA 볼륨 설정: {volume_percent}%")
                    return
                except:
                    pass
                    
            elif system == "Windows":
                # Windows 볼륨 조절
                try:
                    # nircmd 또는 powershell 사용
                    subprocess.run([
                        "powershell", "-c", 
                        f"(New-Object -comObject WScript.Shell).SendKeys([char]175)"
                    ], check=True)
                    print(f"[CoquiTTS] ✅ Windows 볼륨 조절 시도")
                except:
                    pass
                    
            elif system == "Darwin":  # macOS
                try:
                    subprocess.run([
                        "osascript", "-e", f"set volume output volume {volume_percent}"
                    ], check=True)
                    print(f"[CoquiTTS] ✅ macOS 볼륨 설정: {volume_percent}%")
                    return
                except:
                    pass
                    
            print(f"[CoquiTTS] ⚠️ 시스템 볼륨 조절 실패 - 대체 방법 사용")
            
        except Exception as e:
            print(f"[CoquiTTS] ❌ 시스템 볼륨 조절 오류: {e}")
    
    def _apply_audio_volume(self, wav_data: np.ndarray) -> np.ndarray:
        """🆕 오디오 데이터에 직접 볼륨 적용"""
        if self.volume == 0.0:
            # 음소거
            return np.zeros_like(wav_data)
        elif self.volume != 1.0:
            # 볼륨 적용 (클리핑 방지)
            amplified = wav_data.astype(np.float32) * self.volume
            return np.clip(amplified, -32767, 32767).astype(np.int16)
        else:
            return wav_data
    
    def set_voice(self, voice_index: int):
        """음성 설정 (Coqui TTS에서는 모델 변경으로 처리)"""
        print(f"[CoquiTTS] 음성 변경 요청: {voice_index} (모델 변경 필요)")
    
    def get_available_voices(self) -> List:
        """사용 가능한 음성 목록"""
        if self.tts and hasattr(self.tts, 'speakers'):
            return [(i, f"Speaker_{i}", f"speaker_{i}") for i in range(len(self.tts.speakers))]
        return [(0, "Default", "default")]
    
    def is_engine_ready(self) -> bool:
        """엔진 준비 상태"""
        return self.tts is not None and not self.is_loading
    
    def get_current_settings(self) -> dict:
        """현재 설정"""
        return {
            "model_name": self.model_name,
            "rate": self.rate,
            "volume": self.volume,
            "device": self.device,
            "is_speaking": self.is_speaking,
            "is_loading": self.is_loading,
            "engine_ready": self.is_engine_ready()
        }
    
    def __del__(self):
        """소멸자"""
        if self.tts:
            del self.tts 