import time
from typing import Optional, Tuple
from datetime import datetime

# 각 모듈 import - 절대 import로 변경
from audio_io.mic_speaker_io import AudioIO
from stt.whisper_engine import WhisperSTTEngine
from query_parser.request_classifier import RequestClassifier
from request_router.request_executor import RequestExecutor
from tts.tts_engine import TTSEngine
from session_utils.session_manager import SessionManager
from models.request_response_model import (
    VoiceInteraction, AudioData, STTResult, PilotRequest, PilotResponse,
    RequestStatus, create_pilot_request, create_pilot_response
)

class VoiceInteractionController:
    def __init__(self, 
                 audio_io: Optional[AudioIO] = None,
                 stt_engine: Optional[WhisperSTTEngine] = None,
                 query_parser: Optional[RequestClassifier] = None,
                 request_executor: Optional[RequestExecutor] = None,
                 tts_engine: Optional[TTSEngine] = None,
                 session_manager: Optional[SessionManager] = None):
        """
        음성 상호작용 컨트롤러 초기화
        
        Args:
            각 모듈 인스턴스들 (None이면 기본값으로 생성)
        """
        # 모듈 초기화 (None이면 기본 인스턴스 생성)
        self.audio_io = audio_io or AudioIO()
        self.stt_engine = stt_engine or WhisperSTTEngine(model_name="base", language="en", device="auto")
        self.query_parser = query_parser or RequestClassifier()
        self.request_executor = request_executor or RequestExecutor()
        self.tts_engine = tts_engine or TTSEngine()
        self.session_manager = session_manager or SessionManager()
        
        print("[VoiceController] 음성 상호작용 컨트롤러 초기화 완료")
    
    def handle_voice_interaction(self, callsign: str = "UNKNOWN", 
                               recording_duration: float = 5.0) -> VoiceInteraction:
        """
        전체 음성 상호작용 처리 (동기 방식)
        
        Args:
            callsign: 항공기 콜사인
            recording_duration: 녹음 시간 (초)
            
        Returns:
            VoiceInteraction 객체
        """
        # 새 세션 생성
        session_id = self.session_manager.new_session_id()
        
        # 상호작용 객체 생성
        interaction = VoiceInteraction(
            session_id=session_id,
            callsign=callsign
        )
        
        try:
            print(f"[VoiceController] 음성 상호작용 시작: {session_id}")
            
            # 1. 음성 녹음
            print("[VoiceController] 1단계: 음성 녹음")
            audio_data = self._record_audio(recording_duration)
            if not audio_data:
                interaction.mark_failed("음성 녹음 실패")
                return interaction
            
            interaction.audio_input = AudioData(audio_bytes=audio_data)
            
            # 2. STT 처리
            print("[VoiceController] 2단계: 음성 인식")
            stt_result = self._process_stt(audio_data, session_id)
            if not stt_result or not stt_result.text.strip():
                interaction.mark_failed("음성 인식 실패")
                return interaction
            
            interaction.stt_result = stt_result
            
            # 3. 쿼리 분류
            print("[VoiceController] 3단계: 요청 분류")
            request_code, parameters = self._classify_request(stt_result.text, session_id)
            
            # PilotRequest 생성
            pilot_request = create_pilot_request(
                session_id=session_id,
                callsign=callsign,
                text=stt_result.text,
                request_code=request_code,
                parameters=parameters
            )
            pilot_request.confidence_score = stt_result.confidence_score
            interaction.pilot_request = pilot_request
            
            # 4. 요청 처리
            print("[VoiceController] 4단계: 요청 처리")
            response_text = self._execute_request(request_code, parameters, session_id)
            
            # PilotResponse 생성
            pilot_response = create_pilot_response(
                session_id=session_id,
                request_code=request_code,
                response_text=response_text
            )
            interaction.pilot_response = pilot_response
            interaction.tts_text = response_text
            
            # 5. TTS 처리
            print("[VoiceController] 5단계: 음성 합성 및 재생")
            self._process_tts(response_text)
            
            # 상호작용 완료
            interaction.mark_completed()
            
            # 로그 기록
            self._log_interaction(interaction)
            
            print(f"[VoiceController] 음성 상호작용 완료: {session_id}")
            return interaction
            
        except Exception as e:
            print(f"[VoiceController] 음성 상호작용 오류: {e}")
            interaction.mark_failed(str(e))
            return interaction
    
    def handle_voice_interaction_async(self, callsign: str = "UNKNOWN",
                                     recording_duration: float = 5.0,
                                     callback=None) -> str:
        """
        비동기 음성 상호작용 처리
        
        Args:
            callsign: 항공기 콜사인
            recording_duration: 녹음 시간
            callback: 완료 시 호출할 콜백 함수
            
        Returns:
            세션 ID
        """
        import threading
        
        session_id = self.session_manager.new_session_id()
        
        def async_process():
            interaction = self.handle_voice_interaction(callsign, recording_duration)
            if callback:
                callback(interaction)
        
        thread = threading.Thread(target=async_process)
        thread.daemon = True
        thread.start()
        
        return session_id
    
    def start_recording(self):
        """
        녹음 시작 (비동기)
        """
        self.audio_io.start_recording()
    
    def stop_recording_and_process(self, callsign: str = "UNKNOWN") -> VoiceInteraction:
        """
        녹음 중지 및 처리
        """
        # 녹음 중지 및 데이터 획득
        audio_data = self.audio_io.stop_recording()
        
        if not audio_data:
            session_id = self.session_manager.new_session_id()
            interaction = VoiceInteraction(session_id=session_id, callsign=callsign)
            interaction.mark_failed("녹음 데이터 없음")
            return interaction
        
        # 나머지 처리 과정
        return self._process_audio_data(audio_data, callsign)
    
    def _record_audio(self, duration: float) -> bytes:
        """음성 녹음"""
        try:
            return self.audio_io.record_audio(duration)
        except Exception as e:
            print(f"[VoiceController] 녹음 오류: {e}")
            return b""
    
    def _process_stt(self, audio_data: bytes, session_id: str) -> Optional[STTResult]:
        """STT 처리"""
        try:
            start_time = time.time()
            text = self.stt_engine.transcribe(audio_data, session_id)
            processing_time = time.time() - start_time
            
            # 신뢰도 점수가 있는 경우 사용
            if hasattr(self.stt_engine, 'transcribe_with_confidence'):
                text, confidence = self.stt_engine.transcribe_with_confidence(audio_data, session_id)
            else:
                confidence = 0.8  # 기본값
            
            return STTResult(
                text=text,
                confidence_score=confidence,
                processing_time=processing_time,
                model_used="whisper"
            )
        except Exception as e:
            print(f"[VoiceController] STT 처리 오류: {e}")
            return None
    
    def _classify_request(self, text: str, session_id: str) -> Tuple[str, dict]:
        """요청 분류"""
        try:
            return self.query_parser.classify(text, session_id)
        except Exception as e:
            print(f"[VoiceController] 요청 분류 오류: {e}")
            return "UNKNOWN_REQUEST", {"error": str(e)}
    
    def _execute_request(self, request_code: str, parameters: dict, session_id: str) -> str:
        """요청 실행"""
        try:
            return self.request_executor.process_request(request_code, parameters, session_id)
        except Exception as e:
            print(f"[VoiceController] 요청 실행 오류: {e}")
            return f"요청 처리 중 오류가 발생했습니다: {str(e)}"
    
    def _process_tts(self, text: str):
        """TTS 처리"""
        try:
            self.tts_engine.speak(text, blocking=True)
        except Exception as e:
            print(f"[VoiceController] TTS 처리 오류: {e}")
    
    def _process_audio_data(self, audio_data: bytes, callsign: str) -> VoiceInteraction:
        """오디오 데이터 처리 (녹음 완료 후)"""
        session_id = self.session_manager.new_session_id()
        interaction = VoiceInteraction(session_id=session_id, callsign=callsign)
        
        try:
            interaction.audio_input = AudioData(audio_bytes=audio_data)
            
            # STT 처리
            stt_result = self._process_stt(audio_data, session_id)
            if not stt_result:
                interaction.mark_failed("STT 처리 실패")
                return interaction
            
            interaction.stt_result = stt_result
            
            # 나머지 처리 과정
            request_code, parameters = self._classify_request(stt_result.text, session_id)
            
            pilot_request = create_pilot_request(
                session_id=session_id,
                callsign=callsign,
                text=stt_result.text,
                request_code=request_code,
                parameters=parameters
            )
            interaction.pilot_request = pilot_request
            
            response_text = self._execute_request(request_code, parameters, session_id)
            
            pilot_response = create_pilot_response(
                session_id=session_id,
                request_code=request_code,
                response_text=response_text
            )
            interaction.pilot_response = pilot_response
            interaction.tts_text = response_text
            
            # TTS 처리
            self._process_tts(response_text)
            
            interaction.mark_completed()
            self._log_interaction(interaction)
            
            return interaction
            
        except Exception as e:
            interaction.mark_failed(str(e))
            return interaction
    
    def _log_interaction(self, interaction: VoiceInteraction):
        """상호작용 로그 기록"""
        try:
            if interaction.stt_result and interaction.pilot_request and interaction.pilot_response:
                self.session_manager.log_interaction(
                    session_id=interaction.session_id,
                    callsign=interaction.callsign,
                    stt_text=interaction.stt_result.text,
                    request_code=interaction.pilot_request.request_code,
                    parameters=interaction.pilot_request.parameters,
                    response_text=interaction.pilot_response.response_text,
                    processing_time=interaction.total_processing_time,
                    confidence_score=interaction.stt_result.confidence_score
                )
        except Exception as e:
            print(f"[VoiceController] 로그 기록 오류: {e}")
    
    def get_system_status(self) -> dict:
        """시스템 상태 조회"""
        return {
            "audio_io": "OPERATIONAL" if self.audio_io else "FAILED",
            "stt_engine": "OPERATIONAL" if self.stt_engine.is_model_loaded() else "FAILED",
            "query_parser": "OPERATIONAL",
            "request_executor": "OPERATIONAL",
            "tts_engine": "OPERATIONAL" if self.tts_engine.is_engine_ready() else "FAILED",
            "session_manager": "OPERATIONAL",
            "active_sessions": len(self.session_manager.get_active_sessions())
        }
    
    def shutdown(self):
        """컨트롤러 종료"""
        try:
            # 활성 세션들 정리
            for session_id in list(self.session_manager.get_active_sessions().keys()):
                self.session_manager.close_session(session_id)
            
            # TTS 중지
            if self.tts_engine:
                self.tts_engine.stop_speaking()
            
            print("[VoiceController] 컨트롤러 종료 완료")
        except Exception as e:
            print(f"[VoiceController] 종료 중 오류: {e}")
