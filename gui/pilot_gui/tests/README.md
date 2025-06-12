# Pilot GUI Tests

## 폴더 구조

### unit_tests/
개별 컴포넌트에 대한 단위 테스트

- `test_hybrid_tts.py` - 하이브리드 TTS 시스템 테스트
- `quick_tts_test.py` - 빠른 TTS 테스트
- `test_audio_system.py` - 오디오 시스템 테스트
- `test_volume_control.py` - 볼륨 제어 테스트
- `test_improved_tts.py` - 개선된 TTS 테스트
- `test_new_coqui_tts.py` - 새로운 Coqui TTS 테스트
- `test_coqui_tts.py` - Coqui TTS 기본 테스트

### integration_tests/
전체 시스템 통합 테스트

- `test_simple_voice.py` - 간단한 음성 인터페이스 테스트
- `test_callsign_pronunciation.py` - 콜사인 발음 테스트
- `test_aviation_number_conversion.py` - 항공 숫자 변환 테스트
- `test_standard_responses.py` - 표준 응답 시스템 테스트

## 실행 방법

```bash
# 단위 테스트 실행
python -m pytest gui/pilot_gui/tests/unit_tests/

# 통합 테스트 실행
python -m pytest gui/pilot_gui/tests/integration_tests/

# 모든 테스트 실행
python -m pytest gui/pilot_gui/tests/
```

## 기존 테스트 폴더

기존의 테스트 폴더들(`unit/`, `integration/`, `stt/`, `performance/`, `memory/`)은 호환성을 위해 유지됩니다. 