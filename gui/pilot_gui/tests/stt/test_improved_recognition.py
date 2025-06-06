#!/usr/bin/env python3
"""
개선된 인식률 테스트 (Medium 모델 + 강화된 후처리)
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_improved_recognition():
    """개선된 인식률 테스트"""
    print("=== 개선된 인식률 테스트 ===")
    print("🎯 Medium 모델 + GPU + 영어 + 강화된 후처리")
    
    # STT 엔진 초기화
    print("1. STT 엔진 초기화 중...")
    stt_engine = WhisperSTTEngine(model_name="medium", language="en", device="auto")
    
    if not stt_engine.is_model_loaded():
        print("❌ 모델 로딩 실패")
        return
    
    print("✅ Medium 모델 로딩 성공!")
    
    # 오디오 IO 초기화
    print("\n2. 오디오 시스템 초기화...")
    audio_io = AudioIO()
    
    # 테스트 문장들
    test_phrases = [
        "FALCON 123 runway status check",
        "FALCON 456 bird risk assessment", 
        "FALCON 789 request landing clearance",
        "FALCON 101 system status check",
        "FALCON 202 FOD check runway 25L"
    ]
    
    print(f"\n3. 인식률 개선 테스트")
    print("다음 문장들을 하나씩 테스트합니다:")
    for i, phrase in enumerate(test_phrases, 1):
        print(f"  {i}. '{phrase}'")
    
    results = []
    
    for i, target_phrase in enumerate(test_phrases, 1):
        print(f"\n--- 테스트 {i}/5 ---")
        print(f"목표 문장: '{target_phrase}'")
        print("5초 후 녹음을 시작합니다. 위 문장을 정확히 말해주세요.")
        
        # 카운트다운
        for j in range(5, 0, -1):
            print(f"시작까지 {j}초...")
            time.sleep(1)
        
        print("\n🎤 녹음 시작! (5초간)")
        start_time = time.time()
        audio_data = audio_io.record_audio(5.0)
        record_time = time.time() - start_time
        
        if not audio_data:
            print("❌ 녹음 실패")
            continue
        
        print(f"✅ 녹음 완료 ({record_time:.1f}초)")
        
        # STT 처리
        print(f"🔄 음성 인식 처리 중...")
        start_time = time.time()
        recognized_text, confidence = stt_engine.transcribe_with_confidence(audio_data, f"test_{i}")
        stt_time = time.time() - start_time
        
        # 결과 분석
        print(f"\n📊 결과 분석:")
        print(f"  목표: '{target_phrase}'")
        print(f"  인식: '{recognized_text}'")
        print(f"  신뢰도: {confidence:.3f}")
        print(f"  처리시간: {stt_time:.2f}초")
        
        # 정확도 계산 (단어 매칭)
        target_words = set(target_phrase.upper().split())
        recognized_words = set(recognized_text.upper().split())
        
        if target_words and recognized_words:
            accuracy = len(target_words & recognized_words) / len(target_words)
            print(f"  단어 정확도: {accuracy:.1%}")
            
            # 핵심 용어 확인
            key_terms = ["FALCON", "RUNWAY", "BIRD", "LANDING", "SYSTEM", "FOD", "STATUS", "CHECK", "CLEARANCE"]
            target_key_terms = [term for term in key_terms if term in target_phrase.upper()]
            recognized_key_terms = [term for term in key_terms if term in recognized_text.upper()]
            
            if target_key_terms:
                key_accuracy = len(set(target_key_terms) & set(recognized_key_terms)) / len(target_key_terms)
                print(f"  핵심용어 정확도: {key_accuracy:.1%}")
            else:
                key_accuracy = 0
        else:
            accuracy = 0
            key_accuracy = 0
        
        # 평가
        if accuracy >= 0.8:
            print("🎯 우수한 인식률!")
        elif accuracy >= 0.6:
            print("👍 양호한 인식률")
        elif accuracy >= 0.4:
            print("⚠️ 보통 인식률")
        else:
            print("❌ 낮은 인식률")
        
        results.append({
            'target': target_phrase,
            'recognized': recognized_text,
            'confidence': confidence,
            'accuracy': accuracy,
            'key_accuracy': key_accuracy,
            'processing_time': stt_time
        })
        
        print("\n" + "="*50)
    
    # 전체 결과 요약
    print(f"\n🏆 전체 테스트 결과 요약")
    print(f"총 테스트: {len(results)}개")
    
    if results:
        avg_accuracy = sum(r['accuracy'] for r in results) / len(results)
        avg_key_accuracy = sum(r['key_accuracy'] for r in results) / len(results)
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        avg_processing_time = sum(r['processing_time'] for r in results) / len(results)
        
        print(f"평균 단어 정확도: {avg_accuracy:.1%}")
        print(f"평균 핵심용어 정확도: {avg_key_accuracy:.1%}")
        print(f"평균 신뢰도: {avg_confidence:.3f}")
        print(f"평균 처리시간: {avg_processing_time:.2f}초")
        
        # 성능 평가
        if avg_accuracy >= 0.8:
            print("🏆 전체적으로 우수한 성능!")
        elif avg_accuracy >= 0.6:
            print("👍 전체적으로 양호한 성능")
        else:
            print("⚠️ 추가 개선 필요")
    
    print(f"\n💡 개선 사항:")
    print(f"✅ initial_prompt로 항공 용어 힌트 제공")
    print(f"✅ beam_size=5, best_of=5로 정확도 향상")
    print(f"✅ 강화된 후처리로 오인식 패턴 수정")
    print(f"✅ 항공 통신 패턴 자동 복원")

def main():
    try:
        test_improved_recognition()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 