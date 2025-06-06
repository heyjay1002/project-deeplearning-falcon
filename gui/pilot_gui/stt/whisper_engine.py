import whisper
import io
import tempfile
import os
import torch
from typing import Optional

class WhisperSTTEngine:
    def __init__(self, model_name: str = "medium", language: str = "en", device: str = "auto"):
        """
        Whisper STT 엔진 초기화
        
        Args:
            model_name: whisper 모델 크기 (tiny, base, small, medium, large, large-v2, large-v3)
            language: 인식할 언어 코드 (ko, en 등)
            device: 실행 장치 ("auto", "cuda", "cpu")
        """
        self.model_name = model_name
        self.language = language
        self.device = self._determine_device(device)
        self.model = None
        self._setup_gpu_memory()
        self._load_model()
    
    def _determine_device(self, device: str) -> str:
        """
        최적의 실행 장치 결정
        """
        if device == "auto":
            if torch.cuda.is_available():
                # GPU 메모리 확인
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                print(f"[WhisperSTT] GPU 메모리: {gpu_memory:.1f}GB")
                
                # Large 모델을 위해 임계값을 5.5GB로 조정 (100% 사용으로 여유 확보)
                if gpu_memory >= 5.5:
                    return "cuda"
                else:
                    print(f"[WhisperSTT] GPU 메모리 부족 ({gpu_memory:.1f}GB < 5.5GB), CPU 사용")
                    return "cpu"
            else:
                return "cpu"
        return device
    
    def _setup_gpu_memory(self):
        """
        GPU 메모리 최적화 설정
        """
        if self.device == "cuda" and torch.cuda.is_available():
            # GPU 메모리 캐시 정리
            torch.cuda.empty_cache()
            
            # 메모리 할당 전략 설정 - 분할 크기 제한으로 Large 모델 지원
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:256'
            
            # 메모리 분할 방지 - Large 모델을 위해 98%로 설정 (약간의 여유)
            torch.cuda.set_per_process_memory_fraction(0.98)  # GPU 메모리의 98% 사용
            
            print(f"[WhisperSTT] GPU 메모리 최적화 설정 완료 (98% 사용, 분할 제한)")
    
    def _load_model(self):
        """
        Whisper 모델 로딩 - GPU 메모리 최적화 버전
        """
        try:
            print(f"[WhisperSTT] {self.model_name} 모델 로딩 중... (장치: {self.device})")
            
            if self.device == "cuda":
                print(f"[WhisperSTT] GPU 메모리 정리 중...")
                torch.cuda.empty_cache()
                
                # 현재 GPU 메모리 사용량 확인
                allocated = torch.cuda.memory_allocated() / 1024**3
                cached = torch.cuda.memory_reserved() / 1024**3
                print(f"[WhisperSTT] GPU 메모리 - 할당됨: {allocated:.2f}GB, 캐시됨: {cached:.2f}GB")
            
            print(f"[WhisperSTT] 주의: {self.model_name} 모델은 약 3GB 크기로 처음 다운로드 시 시간이 걸릴 수 있습니다.")
            
            # 모델 로딩 시 장치 지정
            self.model = whisper.load_model(self.model_name, device=self.device)
            print(f"[WhisperSTT] {self.model_name} 모델 로딩 완료 - 최고 성능 모드 ({self.device})")
            
        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                print(f"[WhisperSTT] GPU 메모리 부족: {e}")
                print(f"[WhisperSTT] medium 모델로 폴백합니다...")
                try:
                    torch.cuda.empty_cache()  # 메모리 정리
                    self.model = whisper.load_model("medium", device=self.device)
                    self.model_name = "medium"
                    print(f"[WhisperSTT] medium 모델 로딩 완료 ({self.device})")
                except RuntimeError as e2:
                    if "CUDA out of memory" in str(e2):
                        print(f"[WhisperSTT] medium 모델도 실패, CPU로 전환: {e2}")
                        try:
                            self.device = "cpu"
                            self.model = whisper.load_model("medium", device="cpu")
                            self.model_name = "medium"
                            print(f"[WhisperSTT] medium 모델 로딩 완료 (CPU)")
                        except Exception as e3:
                            print(f"[WhisperSTT] CPU에서도 실패, base 모델로 폴백: {e3}")
                            try:
                                self.model = whisper.load_model("base", device="cpu")
                                self.model_name = "base"
                                self.device = "cpu"
                                print(f"[WhisperSTT] base 모델 로딩 완료 (CPU)")
                            except Exception as e4:
                                print(f"[WhisperSTT] 모든 모델 로딩 실패: {e4}")
                                self.model = None
                    else:
                        raise e2
            else:
                raise e
        except Exception as e:
            print(f"[WhisperSTT] 예상치 못한 오류: {e}")
            print(f"[WhisperSTT] base 모델로 폴백합니다...")
            try:
                self.model = whisper.load_model("base", device="cpu")
                self.model_name = "base"
                self.device = "cpu"
                print(f"[WhisperSTT] base 모델 로딩 완료 (CPU)")
            except Exception as e2:
                print(f"[WhisperSTT] 모든 모델 로딩 실패: {e2}")
                self.model = None

    def transcribe(self, audio_bytes: bytes, session_id: str = "") -> str:
        """
        음성 데이터(WAV 바이트) → 텍스트 반환 (GPU 최적화 버전)
        """
        if self.model is None:
            print("[WhisperSTT] 모델이 로드되지 않았습니다.")
            return ""
        
        try:
            # GPU 메모리 정리 (GPU 사용 시)
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            # 임시 파일에 오디오 데이터 저장
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            print(f"[WhisperSTT] 음성 인식 시작... (모델: {self.model_name}, 장치: {self.device}, 세션: {session_id})")
            
            # 모델 크기에 따른 최적화 설정
            if "large" in self.model_name:
                # large 모델용 고품질 설정
                transcribe_options = {
                    "language": self.language,
                    "fp16": self.device == "cuda",  # GPU에서만 fp16 사용
                    "verbose": False,
                    "temperature": 0.0,
                    "beam_size": 5,
                    "best_of": 5,
                    "no_speech_threshold": 0.6,
                    "logprob_threshold": -1.0,
                    "compression_ratio_threshold": 2.4,
                    "condition_on_previous_text": False
                }
            else:
                # medium/base 모델용 기본 설정
                transcribe_options = {
                    "language": self.language,
                    "fp16": False,  # 안정성을 위해 fp16 비활성화
                    "verbose": False,
                    "temperature": 0.0,
                    "condition_on_previous_text": False
                }
            
            # Whisper로 음성 인식
            result = self.model.transcribe(temp_file_path, **transcribe_options)
            
            # 임시 파일 삭제
            os.unlink(temp_file_path)
            
            transcribed_text = result["text"].strip()
            
            # 항공 관련 용어 후처리
            transcribed_text = self._postprocess_aviation_terms(transcribed_text)
            
            print(f"[WhisperSTT] 인식 결과: '{transcribed_text}'")
            
            return transcribed_text
            
        except Exception as e:
            print(f"[WhisperSTT] 음성 인식 오류: {e}")
            # 임시 파일 정리
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return ""
    
    def _postprocess_aviation_terms(self, text: str) -> str:
        """
        영어 항공 관련 용어 정규화 및 후처리
        """
        if not text:
            return text
        
        # 영어 항공 용어 정규화 (잘못 인식되기 쉬운 용어들)
        replacements = {
            # 콜사인 정규화
            "폴콘": "FALCON",
            "팔콘": "FALCON", 
            "falcon": "FALCON",
            "Falcon": "FALCON",
            
            # 숫자 정규화
            "seven eight nine": "789",
            "one two three": "123",
            "four five six": "456",
            "one zero one": "101",
            "two zero two": "202",
            "three zero three": "303",
            
            # 활주로 정규화
            "runway two five left": "runway 25L",
            "runway two five right": "runway 25R", 
            "runway two five": "runway 25",
            "rwy": "runway",
            
            # 항공 용어 정규화
            "clearence": "clearance",
            "clearnce": "clearance",
            "emergancy": "emergency",
            "emergeny": "emergency",
            "assesment": "assessment",
            "assesment": "assessment",
            
            # 한국어 제거 (영어로 복원)
            "허가": "clearance",
            "활주로": "runway",
            "착륙": "landing",
            "이륙": "takeoff",
            "비상": "emergency",
            "조류": "bird",
            "시스템": "system",
            "상태": "status",
            "확인": "check",
            "요청": "request"
        }
        
        # 대소문자 구분 없이 치환
        for old, new in replacements.items():
            # 정확한 단어 매칭을 위해 단어 경계 사용
            import re
            pattern = r'\b' + re.escape(old) + r'\b'
            text = re.sub(pattern, new, text, flags=re.IGNORECASE)
        
        # 연속된 공백 정리
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _postprocess_aviation_terms_enhanced(self, text: str) -> str:
        """
        강화된 영어 항공 관련 용어 정규화 및 후처리
        """
        if not text:
            return text
        
        import re
        
        # 1단계: 일반적인 오인식 패턴 수정
        common_mistakes = {
            # 콜사인 오인식
            "pack": "FALCON",
            "falcon": "FALCON", 
            "falkon": "FALCON",
            "phalcon": "FALCON",
            "pack one": "FALCON 1",
            "pack 1": "FALCON 1",
            "pack to": "FALCON 2",
            "pack 2": "FALCON 2",
            "pack three": "FALCON 3",
            "pack 3": "FALCON 3",
            
            # 숫자 오인식 (더 많은 패턴 추가)
            "want to see": "123",
            "one two three": "123",
            "four five six": "456", 
            "seven eight nine": "789",
            "one zero one": "101",
            "two zero two": "202",
            "three five six": "356",  # 새로 추가
            "one": "1",
            "two": "2", 
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8", 
            "nine": "9",
            "zero": "0",
            
            # 항공 용어 오인식
            "only in": "runway",
            "run way": "runway",
            "run away": "runway",
            "steps": "status",
            "step": "status",
            "check": "check",
            "landing": "landing",
            "take off": "takeoff",
            "clearance": "clearance",
            "clear": "clearance",
            "bird": "bird",
            "system": "system",
            "emergency": "emergency",
            "i'm going to need": "bird risk",  # 새로 추가
            "assistants": "assessment",  # 새로 추가
            "two assistants": "risk assessment",  # 새로 추가
            
            # 활주로 번호
            "25 left": "25L",
            "25 right": "25R",
            "two five left": "25L",
            "two five right": "25R",
            "runway 25": "runway 25"
        }
        
        # 대소문자 구분 없이 치환
        for wrong, correct in common_mistakes.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        # 2단계: 항공 통신 패턴 인식 및 복원
        aviation_patterns = [
            # "FALCON [숫자] [요청]" 패턴
            (r'FALCON\s+(\d+)\s+.*?(runway|landing|bird|system|FOD).*?(status|check|clearance|request)', 
             r'FALCON \1 \2 \3'),
            
            # 활주로 상태 확인
            (r'.*runway.*status.*check.*', 'FALCON runway status check'),
            
            # 조류 위험 확인  
            (r'.*bird.*(risk|check|assessment).*', 'FALCON bird risk assessment'),
            
            # 착륙 허가 요청
            (r'.*(landing|land).*clearance.*', 'FALCON request landing clearance'),
            
            # 시스템 상태 확인
            (r'.*system.*status.*check.*', 'FALCON system status check'),
            
            # FOD 확인
            (r'.*FOD.*check.*', 'FALCON FOD check')
        ]
        
        for pattern, replacement in aviation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 숫자 추출 시도
                numbers = re.findall(r'\d+', text)
                if numbers:
                    callsign = numbers[0]
                    replacement = replacement.replace('FALCON', f'FALCON {callsign}')
                
                text = replacement
                break
        
        # 3단계: 최종 정리
        # 연속된 공백 정리
        text = re.sub(r'\s+', ' ', text)
        
        # 대문자 정규화
        text = text.upper()
        
        return text.strip()

    def transcribe_with_confidence(self, audio_bytes: bytes, session_id: str = "") -> tuple[str, float]:
        """
        음성 인식과 함께 신뢰도 점수 반환 (GPU 최적화 버전)
        """
        if self.model is None:
            return "", 0.0
        
        try:
            # GPU 메모리 정리
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            print(f"[WhisperSTT] 신뢰도 포함 음성 인식... (모델: {self.model_name}, 장치: {self.device})")
            
            # Medium 모델용 고품질 설정 (인식률 개선)
            transcribe_options = {
                "language": self.language,
                "fp16": False,  # 정확도를 위해 fp32 사용
                "verbose": False,
                "temperature": 0.0,  # 가장 확실한 결과만
                "condition_on_previous_text": False,  # 이전 텍스트 영향 제거
                "no_speech_threshold": 0.6,  # 음성 감지 임계값
                "logprob_threshold": -1.0,  # 로그 확률 임계값
                "compression_ratio_threshold": 2.4,  # 압축 비율 임계값
                "beam_size": 5,  # 빔 서치로 정확도 향상
                "best_of": 5,  # 최고 결과 선택
                "initial_prompt": "Aviation radio communication: FALCON callsign, runway, landing, takeoff, clearance, bird, FOD, system status check",  # 항공 용어 힌트
                "suppress_tokens": [-1],  # 반복 토큰 억제
                "word_timestamps": False  # 단어 타임스탬프 비활성화로 안정성 향상
            }
            
            result = self.model.transcribe(temp_file_path, **transcribe_options)
            
            os.unlink(temp_file_path)
            
            text = result["text"].strip()
            
            # 강화된 항공 관련 용어 후처리
            text = self._postprocess_aviation_terms_enhanced(text)
            
            # 신뢰도 계산 (segments 기반)
            avg_confidence = self._calculate_confidence_score(result)
            
            print(f"[WhisperSTT] 인식 결과: '{text}' (신뢰도: {avg_confidence:.3f})")
            
            return text, avg_confidence
            
        except Exception as e:
            print(f"[WhisperSTT] 음성 인식 오류: {e}")
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return "", 0.0
    
    def _calculate_confidence_score(self, result: dict) -> float:
        """
        Whisper 결과에서 신뢰도 점수 계산 (개선된 알고리즘)
        """
        try:
            # segments가 있는 경우 사용
            if "segments" in result and result["segments"]:
                confidences = []
                total_duration = 0
                
                for segment in result["segments"]:
                    segment_duration = segment.get("end", 0) - segment.get("start", 0)
                    total_duration += segment_duration
                    
                    if "avg_logprob" in segment:
                        # log probability를 0-1 범위로 변환 (개선된 공식)
                        logprob = segment["avg_logprob"]
                        # -2.0 ~ 0.0 범위를 0.0 ~ 1.0으로 매핑
                        confidence = max(0.0, min(1.0, (logprob + 2.0) / 2.0))
                        
                        # 세그먼트 길이로 가중평균
                        confidences.append((confidence, segment_duration))
                    
                    # no_speech_prob 반영
                    if "no_speech_prob" in segment:
                        speech_confidence = 1.0 - segment["no_speech_prob"]
                        confidences.append((speech_confidence, segment_duration))
                
                if confidences and total_duration > 0:
                    # 가중평균 계산
                    weighted_sum = sum(conf * duration for conf, duration in confidences)
                    total_weight = sum(duration for _, duration in confidences)
                    return weighted_sum / total_weight if total_weight > 0 else 0.5
            
            # segments가 없는 경우 전체 결과에서 추정
            if "text" in result and result["text"].strip():
                # 텍스트 길이 기반 기본 신뢰도
                text_length = len(result["text"].strip())
                if text_length > 10:
                    return 0.7  # 긴 텍스트는 높은 신뢰도
                elif text_length > 5:
                    return 0.6  # 중간 길이
                else:
                    return 0.5  # 짧은 텍스트
            
            return 0.5  # 기본값
                
        except Exception as e:
            print(f"[WhisperSTT] 신뢰도 계산 오류: {e}")
            return 0.5

    def is_model_loaded(self) -> bool:
        """
        모델 로딩 상태 확인
        """
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """
        현재 모델 정보 반환
        """
        gpu_info = ""
        if torch.cuda.is_available() and self.device == "cuda":
            allocated = torch.cuda.memory_allocated() / 1024**3
            cached = torch.cuda.memory_reserved() / 1024**3
            gpu_info = f" (GPU 메모리: {allocated:.2f}GB 할당, {cached:.2f}GB 캐시)"
        
        return {
            "model_name": self.model_name,
            "language": self.language,
            "device": self.device,
            "is_loaded": self.is_model_loaded(),
            "model_size": "~3GB" if "large" in self.model_name else "~1GB" if "medium" in self.model_name else "~150MB",
            "gpu_memory": gpu_info
        }
    
    def clear_gpu_memory(self):
        """
        GPU 메모리 정리
        """
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("[WhisperSTT] GPU 메모리 정리 완료")
    
    def reload_model(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        모델 재로딩
        """
        if model_name:
            self.model_name = model_name
        if device:
            self.device = self._determine_device(device)
        
        # 기존 모델 정리
        if self.model is not None:
            del self.model
            self.model = None
        
        # GPU 메모리 정리
        self.clear_gpu_memory()
        
        # 새 모델 로딩
        self._setup_gpu_memory()
        self._load_model()
