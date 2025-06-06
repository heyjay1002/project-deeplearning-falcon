#!/usr/bin/env python3
"""
Large-v2 모델 영어 항공 통신 STT 테스트 (최고 정확도)
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_large_english_aviation():
    """Large-v2 모델 영어 항공 통신 STT 테스트"""
    print("=== Large-v2 Model English Aviation STT Test ===")
    print("🎯 최고 정확도 모델 테스트 (GPU 메모리 3GB+ 필요)")
    
    # STT 엔진 초기화 (large-v2 모델, 영어, GPU 자동 선택)
    print("\n1. Initializing Large-v2 STT Engine...")
    stt_engine = WhisperSTTEngine(model_name="large-v2", language="en", device="auto")
    
    # 모델 정보 출력
    model_info = stt_engine.get_model_info()
    print("\nModel Information:")
    for key, value in model_info.items():
        print(f"  {key}: {value}")
    
    if not stt_engine.is_model_loaded():
        print("❌ Large-v2 model loading failed")
        print("💡 Trying fallback to medium model...")
        try:
            stt_engine = WhisperSTTEngine(model_name="medium", language="en", device="auto")
            if stt_engine.is_model_loaded():
                print("✅ Medium model loaded as fallback")
            else:
                print("❌ All models failed to load")
                return
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
            return
    else:
        print("\n🚀 Large-v2 model loaded successfully!")
    
    # 오디오 IO 초기화
    print("\n2. Initializing Audio System...")
    audio_io = AudioIO()
    
    # 테스트 녹음
    print("\n3. Voice Recording Test")
    print("Recording will start in 5 seconds. Please say one of the following:")
    print("- 'FALCON 123 runway status check'")
    print("- 'FALCON 456 bird risk assessment'")
    print("- 'FALCON 789 request landing clearance runway 25 left'")
    print("- 'FALCON 101 system status check'")
    print("- 'FALCON 202 FOD check runway 25L'")
    print("- 'FALCON 303 emergency procedure mayday'")
    
    # 카운트다운
    for i in range(5, 0, -1):
        print(f"Starting in {i} seconds...")
        time.sleep(1)
    
    print("\n🎤 Recording started! (5 seconds)")
    start_time = time.time()
    audio_data = audio_io.record_audio(5.0)
    record_time = time.time() - start_time
    
    if not audio_data:
        print("❌ Recording failed")
        return
    
    print(f"✅ Recording completed ({record_time:.1f}s, {len(audio_data)} bytes)")
    
    # STT 처리
    print(f"\n4. Speech Recognition Processing with {stt_engine.model_name} model...")
    if "large" in stt_engine.model_name:
        print("⏳ Large model processing (may take longer but more accurate)...")
    
    start_time = time.time()
    text, confidence = stt_engine.transcribe_with_confidence(audio_data, "large_test_session")
    stt_time = time.time() - start_time
    
    # 결과 출력
    print(f"\n=== STT Results ({stt_engine.model_name} model) ===")
    print(f"Recognized Text: '{text}'")
    print(f"Confidence Score: {confidence:.3f}")
    print(f"Processing Time: {stt_time:.2f}s")
    print(f"Real-time Ratio: {stt_time/record_time:.2f}x")
    print(f"Device Used: {stt_engine.device}")
    
    # 성능 평가
    if stt_time < record_time:
        print("⚡ Faster than real-time (Excellent)")
    elif stt_time < record_time * 2:
        print("🚀 Within 2x real-time (Good)")
    elif stt_time < record_time * 5:
        print("🐌 Within 5x real-time (Acceptable)")
    elif stt_time < record_time * 10:
        print("🐌🐌 Within 10x real-time (Slow but acceptable for accuracy)")
    else:
        print("🐌🐌🐌 Over 10x real-time (Very slow)")
    
    if confidence > 0.9:
        print("🎯 Excellent Confidence (Outstanding)")
    elif confidence > 0.8:
        print("🎯 High Confidence (Excellent)")
    elif confidence > 0.6:
        print("👍 Medium Confidence (Good)")
    else:
        print("⚠️ Low Confidence (Consider re-recording)")
    
    # 정확도 평가 (영어 항공 용어)
    text_upper = text.upper()
    text_lower = text.lower()
    
    print(f"\n=== Accuracy Assessment ===")
    
    # 콜사인 인식
    if "FALCON" in text_upper:
        print("✅ Callsign Recognition: SUCCESS")
    else:
        print("❌ Callsign Recognition: FAILED")
    
    # 항공 키워드 인식
    aviation_keywords = {
        "runway": ["runway", "rwy"],
        "bird": ["bird", "birds", "wildlife"],
        "landing": ["landing", "land", "approach"],
        "system": ["system", "status"],
        "fod": ["fod", "debris", "foreign object"],
        "clearance": ["clearance", "permission"],
        "check": ["check", "status", "report"],
        "emergency": ["emergency", "mayday", "pan pan"],
        "assessment": ["assessment", "check", "evaluation"]
    }
    
    recognized_keywords = []
    for category, keywords in aviation_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                recognized_keywords.append(category)
                break
    
    if recognized_keywords:
        print(f"✅ Aviation Keywords: {', '.join(recognized_keywords)}")
    else:
        print("❌ Aviation Keywords: None recognized")
    
    # 숫자 인식 확인
    import re
    numbers = re.findall(r'\d+', text)
    if numbers:
        print(f"✅ Numbers Recognized: {', '.join(numbers)}")
    else:
        print("❌ Numbers Recognition: FAILED")
    
    # 활주로 정보 인식
    runway_patterns = [r'runway\s*(\d+[LRC]?)', r'rwy\s*(\d+[LRC]?)', r'(\d+)\s*(left|right|center)']
    runway_found = False
    for pattern in runway_patterns:
        match = re.search(pattern, text_lower)
        if match:
            print(f"✅ Runway Information: {match.group()}")
            runway_found = True
            break
    
    if not runway_found:
        print("❌ Runway Information: Not detected")

def main():
    """메인 함수"""
    try:
        test_large_english_aviation()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Model Comparison Summary ===")
    print("RTX 2060 Performance Comparison:")
    print("🥇 Large-v2 (GPU): Slow but highest accuracy")
    print("🥈 Medium (CPU): Medium speed, high accuracy")  
    print("🥉 Base (GPU): Fast, good accuracy for English")
    print("\n🎯 For Aviation Communication:")
    print("✅ Large-v2: Best for critical communications")
    print("✅ Base: Best for real-time operations")
    print("📝 English is optimal for aviation (ICAO standard)")

if __name__ == "__main__":
    main() 