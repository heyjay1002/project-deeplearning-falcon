아래는 제안한 pilot_gui/ 폴더 구조와 각 서브모듈/파일의 역할 및 책임 설명입니다. 

이 구조는 조종사의 음성 요청 흐름 전체를 책임지는 모듈을 기준으로 한 도메인 기반 아키텍처입니다.

---

📂 controller/
- 📄 voice_interaction_controller.py
    - 전체 흐름의 오케스트레이터 역할 (음성 입력 → STT → LLM → 응답 생성 → TTS)
    - 세션 생성 및 처리 순서 관리
    - 예: run_interaction_loop() 같은 메인 루프 존재

---

📂 stt/
- 📄 whisper_engine.py
    - Whisper 모델을 로드하고, Base64로 전달된 음성 데이터를 텍스트로 변환
    - 로컬 또는 서버 기반 처리 모두 가능
    - 함수 예: transcribe_audio(audio_base64, language)

---

📂 query_parser/ (기존 LLM 역할 일부 담당)
- 📄 request_classifier.py
    - 텍스트 질의(query_text)를 받아서 request_code 또는 request_id로 변환
    - 간단한 룰 기반 혹은 미니 LLM 파인튜닝 모델 가능
    - 예: "현재 조류 위험도는?" → "BIRD_RISK"

---

📂 request_router/
- 📄 request_executor.py
    - request_code에 따라 실제 처리 분기 (ex: DB 조회, 캐시 조회 등)
    - 필요한 경우 응답 텍스트까지 구성 (e.g., response_text, response_code)

---

📂 tts/
- 📄 tts_engine.py
    - 입력된 텍스트(response_text)를 음성으로 변환하고 Base64로 인코딩
    - 예: generate_audio(text: str) -> base64_audio

---

📂 audio_io/
- 📄 mic_speaker_io.py
    - 마이크 입력 / 스피커 출력 담당
    - record_audio() 및 play_audio(base64_audio) 함수 포함

---

📂 session_utils/
- 📄 session_manager.py
- 세션 ID 생성, 로그 저장, 시간 기록 등 유틸 기능 제공
- 예: generate_session_id(), log_interaction(session_id, ...)

---

📂 models/
- 📄 request_response_model.py
- 데이터 구조 정의 (e.g., PilotRequest, PilotResponse 클래스)
- 내부 메시지 포맷에 대한 pydantic 모델 또는 dataclass 등 정의

```
class PilotRequest(BaseModel):
    request_code: str
    parameters: Dict
    session_id: str
```

---

✅ 이 구조의 장점
- 기능 단위로 명확하게 분리되어 유지보수가 쉬움
- 각 모듈이 테스트 가능하고, 교체 용이 (Whisper → 다른 STT 등)
- 파일 명이 책임을 직접적으로 표현하여 다른 개발자도 이해하기 쉬움

