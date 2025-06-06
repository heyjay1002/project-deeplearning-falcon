#!/usr/bin/env python3
"""
Medium 모델 CPU STT 테스트 (한국어 정확도 우선)
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_medium_cpu():
    """Medium 모델 CPU 테스트"""
    print("=== Medium 모델 CPU STT 테스트 (한국어 정확도 우선) ===")
    
    # STT 엔진 초기화 (medium 모델, CPU 강제)
    print("1. STT 엔진 초기화 중...")
    stt_engine = WhisperSTTEngine(model_name="medium", language="ko", device="cpu")
    
    # 모델 정보 출력
    model_info = stt_engine.get_model_info()
    print("\n모델 정보:")
    for key, value in model_info.items():
        print(f"  {key}: {value}")
    
    if not stt_engine.is_model_loaded():
        print("❌ 모델 로딩 실패")
        return
    
    print("\n✅ 모델 로딩 성공!")
    
    # 오디오 IO 초기화
    print("\n2. 오디오 시스템 초기화 중...")
    audio_io = AudioIO()
    
    # 테스트 녹음
    print("\n3. 음성 녹음 테스트")
    print("5초 후 녹음을 시작합니다. 다음 중 하나를 말해보세요:")
    print("- 'FALCON 123 활주로 상태 확인 요청'")
    print("- 'FALCON 456 조류 위험도 체크'")
    print("- 'FALCON 789 착륙 허가 요청'")
    
    # 카운트다운
    for i in range(5, 0, -1):
        print(f"시작까지 {i}초...")
        time.sleep(1)
    
    print("\n🎤 녹음 시작! (5초간)")
    start_time = time.time()
    audio_data = audio_io.record_audio(5.0)
    record_time = time.time() - start_time
    
    if not audio_data:
        print("❌ 녹음 실패")
        return
    
    print(f"✅ 녹음 완료 ({record_time:.1f}초, {len(audio_data)} bytes)")
    
    # STT 처리
    print("\n4. 음성 인식 처리 중... (CPU에서 처리되므로 시간이 걸립니다)")
    start_time = time.time()
    text, confidence = stt_engine.transcribe_with_confidence(audio_data, "test_session")
    stt_time = time.time() - start_time
    
    # 결과 출력
    print(f"\n=== STT 결과 ===")
    print(f"인식된 텍스트: '{text}'")
    print(f"신뢰도 점수: {confidence:.3f}")
    print(f"처리 시간: {stt_time:.2f}초")
    print(f"실시간 비율: {stt_time/record_time:.2f}x")
    
    # 성능 평가
    if stt_time < record_time * 2:
        print("⚡ 실시간 대비 2배 이내 (양호)")
    elif stt_time < record_time * 5:
        print("🐌 실시간 대비 5배 이내 (허용 가능)")
    else:
        print("🐌🐌 실시간 대비 5배 초과 (느림)")
    
    if confidence > 0.8:
        print("🎯 높은 신뢰도 (우수)")
    elif confidence > 0.6:
        print("👍 보통 신뢰도 (양호)")
    else:
        print("⚠️ 낮은 신뢰도 (재녹음 권장)")
    
    # 정확도 평가
    if "FALCON" in text.upper() or "팔콘" in text or "폴콘" in text:
        print("✅ 콜사인 인식 성공")
    else:
        print("❌ 콜사인 인식 실패")
    
    if "활주로" in text or "runway" in text.lower():
        print("✅ 활주로 키워드 인식 성공")
    elif "조류" in text or "bird" in text.lower():
        print("✅ 조류 키워드 인식 성공")
    elif "착륙" in text or "landing" in text.lower():
        print("✅ 착륙 키워드 인식 성공")
    else:
        print("❌ 주요 키워드 인식 실패")

def main():
    """메인 함수"""
    try:
        test_medium_cpu()
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    
    print("\n=== 최종 권장사항 ===")
    print("RTX 2060 환경에서의 최적 설정:")
    print("✅ Medium 모델 (CPU): 느리지만 정확한 한국어 인식")
    print("❌ Base 모델 (GPU): 빠르지만 한국어 인식 성능 매우 부족")
    print("⚖️ 트레이드오프: 속도 vs 정확도")
    print("📝 항공 통신에서는 정확도가 더 중요하므로 Medium(CPU) 권장")

if __name__ == "__main__":
    main() 