#!/usr/bin/env python3
"""
Medium 모델 GPU 테스트 스크립트
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_medium_gpu():
    """Medium 모델 GPU 테스트"""
    print("=== Medium 모델 GPU 테스트 ===")
    
    # STT 엔진 초기화 (기본값이 medium으로 변경됨)
    print("1. STT 엔진 초기화 중...")
    stt_engine = WhisperSTTEngine()
    
    # 모델 정보 출력
    print(f"\n모델 정보:")
    print(f"  모델명: {stt_engine.model_name}")
    print(f"  장치: {stt_engine.device}")
    print(f"  언어: {stt_engine.language}")
    print(f"  로딩 상태: {stt_engine.is_model_loaded()}")
    
    if not stt_engine.is_model_loaded():
        print("❌ 모델 로딩 실패")
        return
    
    print("✅ Medium 모델 GPU 로딩 성공!")
    
    # 오디오 IO 초기화
    print("\n2. 오디오 시스템 초기화...")
    audio_io = AudioIO()
    
    # 음성 테스트
    print("\n3. 음성 인식 테스트")
    print("5초 후 녹음을 시작합니다. 다음 중 하나를 말해주세요:")
    print("- 'FALCON 123 runway status check'")
    print("- 'FALCON 456 bird risk assessment'")
    print("- 'FALCON 789 request landing clearance'")
    
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
    print(f"\n4. Medium 모델 음성 인식 처리...")
    start_time = time.time()
    text, confidence = stt_engine.transcribe_with_confidence(audio_data, "medium_test")
    stt_time = time.time() - start_time
    
    # 결과 출력
    print(f"\n=== 결과 ===")
    print(f"인식된 텍스트: '{text}'")
    print(f"신뢰도: {confidence:.3f}")
    print(f"처리 시간: {stt_time:.2f}초")
    print(f"실시간 비율: {stt_time/record_time:.2f}x")
    
    # 성능 평가
    if stt_time < record_time:
        print("⚡ 실시간보다 빠름 (우수)")
    elif stt_time < record_time * 2:
        print("🚀 실시간의 2배 이내 (양호)")
    else:
        print("🐌 실시간의 2배 초과 (느림)")
    
    if confidence > 0.8:
        print("🎯 높은 신뢰도 (우수)")
    elif confidence > 0.6:
        print("👍 보통 신뢰도 (양호)")
    else:
        print("⚠️ 낮은 신뢰도 (재녹음 권장)")
    
    # GPU 메모리 사용량 확인
    import torch
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated() / 1024**3
        print(f"\n💾 현재 GPU 메모리 사용량: {gpu_memory:.2f}GB")

def main():
    try:
        test_medium_gpu()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 