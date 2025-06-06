#!/usr/bin/env python3
"""
Base 모델 STT 성능 테스트 (RTX 2060 최적화)
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_base_model():
    """Base 모델 테스트"""
    print("=== Base 모델 STT 테스트 (RTX 2060 최적화) ===")
    
    # STT 엔진 초기화 (base 모델, GPU 자동 선택)
    print("1. STT 엔진 초기화 중...")
    stt_engine = WhisperSTTEngine(model_name="base", language="ko", device="auto")
    
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
    print("\n4. 음성 인식 처리 중...")
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
    if stt_time < record_time:
        print("🚀 실시간보다 빠른 처리 (우수)")
    elif stt_time < record_time * 2:
        print("⚡ 실시간 대비 2배 이내 (양호)")
    else:
        print("🐌 실시간 대비 2배 초과 (개선 필요)")
    
    if confidence > 0.7:
        print("🎯 높은 신뢰도 (우수)")
    elif confidence > 0.5:
        print("👍 보통 신뢰도 (양호)")
    else:
        print("⚠️ 낮은 신뢰도 (재녹음 권장)")
    
    # GPU 메모리 사용량 확인
    if stt_engine.device == "cuda":
        import torch
        allocated = torch.cuda.memory_allocated() / 1024**3
        print(f"💾 GPU 메모리 사용량: {allocated:.2f}GB")

def main():
    """메인 함수"""
    try:
        test_base_model()
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    
    print("\n=== 테스트 완료 ===")
    print("Base 모델은 RTX 2060에서 안정적이고 빠른 성능을 제공합니다.")
    print("성능 vs 정확도:")
    print("- Base (GPU): 빠름, 보통 정확도 ⭐ 권장 (RTX 2060)")
    print("- Medium (CPU): 느림, 높은 정확도")
    print("- Large-v2 (CPU): 매우 느림, 최고 정확도")

if __name__ == "__main__":
    main() 