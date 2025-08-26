import time
import logging
from typing import Optional, Tuple
from datetime import datetime

# 로컬 모듈 및 설정 파일 임포트
from audio_io.mic_speaker_io import AudioIO
from engine import WhisperSTTEngine, UnifiedTTSEngine
from request_handler import RequestClassifier, TCPServerClient, ResponseProcessor
from session_handler import SessionManager
from .voice_models import VoiceInteraction, AudioData, STTResult
from request_handler.request_models import (
    PilotRequest, PilotResponse, RequestStatus, 
    create_pilot_request, create_pilot_response
)
from config import settings as cfg

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class VoiceInteractionController:
    """음성 상호작용의 전체 흐름을 제어하는 컨트롤러"""
    
    def __init__(self, 
                 audio_io: Optional[AudioIO] = None,
                 stt_engine: Optional[WhisperSTTEngine] = None,
                 query_parser: Optional[RequestClassifier] = None,
                 main_server_client: Optional[TCPServerClient] = None,
                 response_processor: Optional[ResponseProcessor] = None,
                 tts_engine: Optional[UnifiedTTSEngine] = None,
                 session_manager: Optional[SessionManager] = None):
        """
        음성 상호작용 컨트롤러를 초기화합니다.
        제공되지 않은 모듈은 설정값에 따라 기본 인스턴스로 생성됩니다.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # 모듈 초기화
        self.audio_io = audio_io or AudioIO.create_with_best_mic()
        self.stt_engine = stt_engine or WhisperSTTEngine(
            model_name=cfg.STT_MODEL_NAME, 
            language=cfg.STT_LANGUAGE, 
            device=cfg.STT_DEVICE
        )
        self.query_parser = query_parser or RequestClassifier()
        self.main_server_client = main_server_client or TCPServerClient()
        self.response_processor = response_processor or ResponseProcessor()
        self.tts_engine = tts_engine or UnifiedTTSEngine(
            use_coqui=cfg.TTS_USE_COQUI,
            coqui_model=cfg.TTS_COQUI_MODEL,
            fallback_to_pyttsx3=cfg.TTS_FALLBACK_TO_PYTTSX3,
            device=cfg.TTS_DEVICE
        )
        self.session_manager = session_manager or SessionManager()
        
        self.stt_callback = None
        self.tts_callback = None
        
        self._initialize_features()
        self.logger.info("음성 상호작용 컨트롤러 초기화 완료")

    def _initialize_features(self):
        """부가 기능(LLM, TTS 엔진)을 초기화하고 상태를 로깅합니다."""
        if hasattr(self.query_parser, 'enable_llm'):
            if self.query_parser.enable_llm():
                self.logger.info("LLM 하이브리드 분류 활성화됨.")
            else:
                self.logger.warning("LLM 비활성화, 키워드 기반 분류만 사용됩니다.")
        
        if hasattr(self.tts_engine, 'get_status'):
            tts_status = self.tts_engine.get_status()
            self.logger.info(f"TTS 엔진 상태: {tts_status.get('current_engine', 'Unknown')}")

    def handle_voice_interaction(self, callsign: str = cfg.DEFAULT_CALLSIGN, 
                               recording_duration: float = cfg.DEFAULT_RECORDING_DURATION) -> VoiceInteraction:
        """전체 음성 상호작용 사이클을 동기 방식으로 처리합니다."""
        session_id = self.session_manager.new_session_id()
        interaction = VoiceInteraction(session_id=session_id, callsign=callsign)
        self.logger.info(f"음성 상호작용 시작: 세션 ID {session_id}")

        try:
            # 1. 음성 녹음 및 STT
            stt_result = self._record_and_transcribe(interaction, recording_duration)
            if not stt_result:
                return interaction # 실패 처리는 내부 메서드에서 수행

            # 2. 요청 분류 및 실행
            response_text = self._classify_and_execute(interaction, stt_result)
            if not response_text:
                return interaction # 실패 처리는 내부 메서드에서 수행

            # 3. TTS 음성 합성 및 재생
            self._synthesize_and_play(interaction, response_text)

            interaction.mark_completed()
            self._log_interaction(interaction)
            self.logger.info(f"음성 상호작용 성공: 세션 ID {session_id}")

        except Exception as e:
            self.logger.exception(f"음성 상호작용 중 심각한 오류 발생: {e}")
            interaction.mark_failed(str(e))
        
        return interaction

    def _record_and_transcribe(self, interaction: VoiceInteraction, duration: float) -> Optional[STTResult]:
        """음성을 녹음하고 텍스트로 변환합니다."""
        self.logger.info("1. 음성 녹음 중...")
        audio_data = self.audio_io.record_audio(duration)
        if not audio_data:
            interaction.mark_failed("음성 녹음 실패")
            self.logger.error("녹음된 오디오 데이터가 없습니다.")
            return None
        interaction.audio_input = AudioData(audio_bytes=audio_data)

        self.logger.info("2. 음성 인식(STT) 처리 중...")
        stt_result = self._process_stt(audio_data, interaction.session_id)
        if not stt_result or not stt_result.text.strip():
            interaction.mark_failed("음성 인식 실패")
            self.logger.error("STT 결과가 비어있습니다.")
            return None
        interaction.stt_result = stt_result
        
        if self.stt_callback:
            self.stt_callback(stt_result)
        return stt_result

    def _classify_and_execute(self, interaction: VoiceInteraction, stt_result: STTResult) -> Optional[str]:
        """인식된 텍스트를 분류하고, 요청을 실행하여 응답 텍스트를 반환합니다."""
        self.logger.info("3. 요청 분류 중...")
        request_code, parameters = self._classify_request_hybrid(stt_result.text, interaction.session_id)
        
        pilot_request = create_pilot_request(
            session_id=interaction.session_id, callsign=interaction.callsign,
            text=stt_result.text, request_code=request_code, parameters=parameters
        )
        pilot_request.confidence_score = stt_result.confidence_score
        interaction.pilot_request = pilot_request

        self.logger.info("4. 구조화된 질의 처리 중...")
        if request_code != "UNKNOWN_REQUEST":
            response_text = self._execute_structured_query(request_code, parameters, interaction.session_id)
        else:
            response_text = self._execute_request(request_code, parameters, interaction.session_id)
        
        if not response_text:
             interaction.mark_failed("요청 실행 실패")
             self.logger.error("요청 실행 후 응답 텍스트가 없습니다.")
             return None

        return response_text

    def _synthesize_and_play(self, interaction: VoiceInteraction, text: str):
        """응답 텍스트를 음성으로 합성하고 재생합니다."""
        interaction.pilot_response = create_pilot_response(
            session_id=interaction.session_id,
            request_code=interaction.pilot_request.request_code,
            response_text=text
        )
        interaction.tts_text = text

        if self.tts_callback:
            self.tts_callback(text)

        self.logger.info("5. 음성 합성(TTS) 및 재생 중...")
        self._process_tts(text)

    def _classify_request_hybrid(self, text: str, session_id: str) -> Tuple[str, dict]:
        """하이브리드 요청 분류 (LLM + 키워드)를 수행합니다."""
        try:
            if hasattr(self.query_parser, 'classify_hybrid'):
                return self.query_parser.classify_hybrid(text, session_id)
            else:
                return self.query_parser.classify(text, session_id)
        except Exception as e:
            self.logger.exception(f"요청 분류 중 오류 발생: {e}")
            return "UNKNOWN_REQUEST", {"error": str(e), "original_text": text}

    def _execute_structured_query(self, request_code: str, parameters: dict, session_id: str) -> str:
        """구조화된 질의를 메인 서버로 보내고 응답을 처리합니다."""
        try:
            self.logger.info(f"메인 서버 질의 전송: {request_code}")
            success, response_data = self.main_server_client.send_query(request_code, parameters, session_id)
            
            if not success:
                self.logger.error(f"서버 질의 실패: {response_data}. 일반 요청으로 폴백합니다.")
                return self._execute_request(request_code, parameters, session_id)
            
            is_valid, validation_msg = self.response_processor.validate_response_data(response_data)
            if not is_valid:
                self.logger.warning(f"수신된 응답 데이터가 유효하지 않음: {validation_msg}. 일반 요청으로 폴백합니다.")
                return self._execute_request(request_code, parameters, session_id)
            
            self.logger.info(f"서버 응답 수신: {self.response_processor.get_response_summary(response_data)}")
            original_request = {
                "callsign": parameters.get("callsign", "Aircraft"),
                "request_text": parameters.get("original_text", "unknown request"),
                "parameters": parameters
            }
            
            success, response_text = self.response_processor.process_response(response_data, original_request)
            
            if success:
                self.logger.info(f"구조화된 응답 생성 완료: '{response_text}'")
                return response_text
            else:
                self.logger.warning(f"응답 처리 실패({response_text}), 일반 요청으로 폴백합니다.")
                return self._execute_request(request_code, parameters, session_id)
                
        except Exception as e:
            self.logger.exception(f"구조화된 질의 처리 중 오류 발생: {e}")
            return self._execute_request(request_code, parameters, session_id)

    def _process_stt(self, audio_data: bytes, session_id: str) -> Optional[STTResult]:
        """STT 처리를 수행하고 결과를 반환합니다."""
        try:
            start_time = time.time()
            if hasattr(self.stt_engine, 'transcribe_with_confidence'):
                text, confidence = self.stt_engine.transcribe_with_confidence(audio_data, session_id)
            else:
                text = self.stt_engine.transcribe(audio_data, session_id)
                confidence = 0.8  # 기본 신뢰도
            
            return STTResult(
                text=text, confidence_score=confidence,
                processing_time=(time.time() - start_time), model_used="whisper"
            )
        except Exception as e:
            self.logger.exception(f"STT 처리 중 오류 발생: {e}")
            return None

    def _execute_request(self, request_code: str, parameters: dict, session_id: str) -> str:
        """(폴백) 요청을 실행합니다."""
        try:
            self.logger.info(f"MockMainServer 기반 요청 처리: {request_code}")
            success, response_data = self.main_server_client.send_query(request_code, parameters, session_id)
            
            if success:
                original_request = {
                    "request_code": request_code,
                    "callsign": parameters.get("callsign", "Aircraft"),
                    "original_text": parameters.get("original_text", "")
                }
                success_processed, final_response = self.response_processor.process_response(response_data, original_request)
                return final_response if success_processed else "응답 처리 중 오류가 발생했습니다."
            else:
                self.logger.error(f"서버 질의 실패: {response_data}")
                return "요청 처리에 실패했습니다. 다시 시도해주세요."
                
        except Exception as e:
            self.logger.exception(f"요청 실행 중 오류 발생: {e}")
            return f"요청 처리 중 오류가 발생했습니다: {str(e)}"

    def _process_tts(self, text: str):
        """TTS 처리를 수행합니다."""
        try:
            self.logger.info(f"TTS 처리 텍스트: '{text}'")
            # tts_type 인자를 지원하는 경우 "response" 타입으로 지정
            if hasattr(self.tts_engine, 'speak') and 'tts_type' in self.tts_engine.speak.__code__.co_varnames:
                self.tts_engine.speak(text, blocking=True, tts_type="response")
            else:
                self.tts_engine.speak(text, blocking=True)
        except Exception as e:
            self.logger.exception(f"TTS 처리 중 오류 발생: {e}")

    def _log_interaction(self, interaction: VoiceInteraction):
        """상호작용 내용을 세션 매니저에 기록합니다."""
        try:
            if interaction.stt_result and interaction.pilot_request and interaction.pilot_response:
                self.session_manager.log_interaction(
                    session_id=interaction.session_id, callsign=interaction.callsign,
                    stt_text=interaction.stt_result.text, request_code=interaction.pilot_request.request_code,
                    parameters=interaction.pilot_request.parameters, response_text=interaction.pilot_response.response_text,
                    processing_time=interaction.total_processing_time, confidence_score=interaction.stt_result.confidence_score
                )
        except Exception as e:
            self.logger.error(f"로그 기록 중 오류 발생: {e}")

    def shutdown(self):
        """시스템을 종료하고 리소스를 정리합니다."""
        self.logger.info("시스템 종료 중...")
        try:
            if self.tts_engine:
                if hasattr(self.tts_engine, 'shutdown'): self.tts_engine.shutdown()
                else: self.tts_engine.stop_speaking()
            
            if self.main_server_client and hasattr(self.main_server_client, 'shutdown'):
                self.main_server_client.shutdown()
            
            if self.audio_io:
                if hasattr(self.audio_io, 'stop_recording'): self.audio_io.stop_recording()
                if hasattr(self.audio_io, 'shutdown'): self.audio_io.shutdown()
            
            self.logger.info("시스템 종료 완료.")
        except Exception as e:
            self.logger.exception(f"시스템 종료 중 오류 발생: {e}")

    def set_stt_callback(self, callback):
        """STT 완료 시 호출될 콜백 함수를 설정합니다."""
        self.stt_callback = callback
        self.logger.info("STT 완료 콜백이 설정되었습니다.")

    def set_tts_callback(self, callback):
        """TTS 텍스트 생성 완료 시 호출될 콜백 함수를 설정합니다."""
        self.tts_callback = callback
        self.logger.info("TTS 텍스트 생성 콜백이 설정되었습니다.")

# 편의 함수
def create_voice_controller(
    server_host: str = cfg.DEFAULT_HOST,
    server_port: int = cfg.MAIN_SERVER_PORT,
    use_simulator: bool = True,
    stt_model: str = cfg.STT_MODEL_NAME
) -> VoiceInteractionController:
    """
    VoiceInteractionController의 인스턴스를 생성합니다.
    TCP 기반의 구조화된 질의 시스템을 사용합니다.
    """
    try:
        logger = logging.getLogger("create_voice_controller")
        logger.info("TCP 기반 구조화된 질의 시스템 초기화 중...")
        logger.info(f"  - 서버: {server_host}:{server_port}")
        logger.info(f"  - 시뮬레이터 폴백: {'활성화' if use_simulator else '비활성화'}")
        
        # 모듈 인스턴스 생성
        audio_io = AudioIO.create_with_best_mic()
        stt_engine = WhisperSTTEngine(model_name=stt_model, language=cfg.STT_LANGUAGE, device=cfg.STT_DEVICE)
        query_parser = RequestClassifier()
        main_server_client = TCPServerClient(server_host=server_host, server_port=server_port, use_simulator=use_simulator)
        response_processor = ResponseProcessor()
        tts_engine = UnifiedTTSEngine(
            use_coqui=cfg.TTS_USE_COQUI, coqui_model=cfg.TTS_COQUI_MODEL,
            fallback_to_pyttsx3=cfg.TTS_FALLBACK_TO_PYTTSX3, device=cfg.TTS_DEVICE
        )
        session_manager = SessionManager()
        
        # 컨트롤러 생성
        controller = VoiceInteractionController(
            audio_io=audio_io, stt_engine=stt_engine, query_parser=query_parser,
            main_server_client=main_server_client, response_processor=response_processor,
            tts_engine=tts_engine, session_manager=session_manager
        )
        
        logger.info("TCP 기반 구조화된 질의 시스템 초기화 완료.")
        return controller
        
    except Exception as e:
        logging.getLogger("create_voice_controller").exception(f"컨트롤러 생성 실패: {e}")
        raise