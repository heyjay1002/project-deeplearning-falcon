#!/usr/bin/env python3
"""
영어 항공 통신 STT 테스트 (Base 모델 GPU)
"""

import time
from stt.whisper_engine import WhisperSTTEngine
from audio_io.mic_speaker_io import AudioIO

def test_english_aviation():
    """영어 항공 통신 STT 테스트"""
    print("=== English Aviation Communication STT Test ===")
    
    # STT 엔진 초기화 (base 모델, 영어, GPU 자동 선택)
    print("1. Initializing STT Engine...")
    stt_engine = WhisperSTTEngine(model_name="base", language="en", device="auto")
    
    # 모델 정보 출력
    model_info = stt_engine.get_model_info()
    print("\nModel Information:")
    for key, value in model_info.items():
        print(f"  {key}: {value}")
    
    if not stt_engine.is_model_loaded():
        print("❌ Model loading failed")
        return
    
    print("\n✅ Model loaded successfully!")
    
    # 오디오 IO 초기화
    print("\n2. Initializing Audio System...")
    audio_io = AudioIO()
    
    # 테스트 녹음
    print("\n3. Voice Recording Test")
    print("Recording will start in 5 seconds. Please say one of the following:")
    print("- 'FALCON 123 runway status check'")
    print("- 'FALCON 456 bird risk check'")
    print("- 'FALCON 789 request landing clearance'")
    print("- 'FALCON 101 system status check'")
    print("- 'FALCON 202 FOD check runway 25L'")
    
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
    print("\n4. Speech Recognition Processing...")
    start_time = time.time()
    text, confidence = stt_engine.transcribe_with_confidence(audio_data, "test_session")
    stt_time = time.time() - start_time
    
    # 결과 출력
    print(f"\n=== STT Results ===")
    print(f"Recognized Text: '{text}'")
    print(f"Confidence Score: {confidence:.3f}")
    print(f"Processing Time: {stt_time:.2f}s")
    print(f"Real-time Ratio: {stt_time/record_time:.2f}x")
    
    # 성능 평가
    if stt_time < record_time:
        print("⚡ Faster than real-time (Excellent)")
    elif stt_time < record_time * 2:
        print("🚀 Within 2x real-time (Good)")
    elif stt_time < record_time * 5:
        print("🐌 Within 5x real-time (Acceptable)")
    else:
        print("🐌🐌 Over 5x real-time (Slow)")
    
    if confidence > 0.8:
        print("🎯 High Confidence (Excellent)")
    elif confidence > 0.6:
        print("👍 Medium Confidence (Good)")
    else:
        print("⚠️ Low Confidence (Consider re-recording)")
    
    # 정확도 평가 (영어 항공 용어)
    text_upper = text.upper()
    
    if "FALCON" in text_upper:
        print("✅ Callsign Recognition: SUCCESS")
    else:
        print("❌ Callsign Recognition: FAILED")
    
    aviation_keywords = {
        "runway": ["runway", "rwy"],
        "bird": ["bird", "birds", "wildlife"],
        "landing": ["landing", "land", "approach"],
        "system": ["system", "status"],
        "fod": ["fod", "debris", "foreign object"],
        "clearance": ["clearance", "permission"],
        "check": ["check", "status", "report"]
    }
    
    recognized_keywords = []
    for category, keywords in aviation_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
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

def main():
    """메인 함수"""
    try:
        test_english_aviation()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
    
    print("\n=== Final Recommendations ===")
    print("For RTX 2060 Environment:")
    print("✅ Base Model (GPU) + English: Fast and accurate for aviation")
    print("❌ Base Model (GPU) + Korean: Fast but poor accuracy")
    print("✅ Medium Model (CPU) + Korean: Slow but accurate")
    print("🎯 English Aviation Communication: RECOMMENDED")
    print("📝 ICAO Standard: English is the international aviation language")

if __name__ == "__main__":
    main() 