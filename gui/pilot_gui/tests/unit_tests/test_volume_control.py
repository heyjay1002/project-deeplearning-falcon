#!/usr/bin/env python3
"""
SPK VOLUME 슬라이더 볼륨 조절 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui/pilot_gui'))

def test_volume_control():
    """볼륨 조절 기능 테스트"""
    print("🔊 SPK VOLUME 슬라이더 볼륨 조절 테스트")
    print("=" * 50)
    
    try:
        from tts.hybrid_tts_engine import HybridTTSEngine
        
        print("1️⃣ 하이브리드 TTS 엔진 초기화 중...")
        tts_engine = HybridTTSEngine(
            use_coqui=True,
            coqui_model="tts_models/en/ljspeech/tacotron2-DDC",
            fallback_to_pyttsx3=True
        )
        
        if not tts_engine.is_engine_ready():
            print("❌ TTS 엔진이 준비되지 않음")
            return
        
        print("✅ TTS 엔진 준비 완료")
        print(f"   현재 엔진: {tts_engine.get_current_engine()}")
        
        # 볼륨 테스트 시퀀스
        test_text = "Volume test. This is volume level"
        
        volume_levels = [100, 50, 25, 10, 0, 25, 50, 100]
        
        for i, volume in enumerate(volume_levels):
            print(f"\n{i+1}️⃣ 볼륨 {volume}% 테스트")
            
            # 볼륨 설정
            volume_normalized = volume / 100.0
            tts_engine.set_volume(volume_normalized)
            
            # 현재 볼륨 확인
            current_volume = tts_engine.get_current_volume()
            print(f"   설정된 볼륨: {current_volume:.2f} ({volume}%)")
            
            # 음성 재생
            if volume == 0:
                print("   🔇 음소거 상태 - 음성 재생 생략됨")
                tts_engine.speak(f"{test_text} {volume} percent", blocking=True)
            else:
                print(f"   🔊 음성 재생 중... (볼륨: {volume}%)")
                tts_engine.speak(f"{test_text} {volume} percent", blocking=True)
            
            # 사용자 입력 대기
            if i < len(volume_levels) - 1:
                input("   👂 소리가 들렸나요? [Enter]를 눌러 다음 테스트로...")
        
        print("\n✅ 볼륨 조절 테스트 완료!")
        print("\n📋 테스트 결과:")
        print("   - 볼륨 100%: 최대 음량")
        print("   - 볼륨 50%: 중간 음량")  
        print("   - 볼륨 25%: 낮은 음량")
        print("   - 볼륨 10%: 매우 낮은 음량")
        print("   - 볼륨 0%: 음소거 (소리 없음)")
        
        # 사용자 피드백
        feedback = input("\n💬 볼륨 조절이 제대로 작동했나요? (y/n): ").lower().strip()
        if feedback == 'y':
            print("✅ 볼륨 조절 기능 정상 작동!")
        else:
            print("❌ 볼륨 조절 기능에 문제가 있습니다.")
            print("   - Coqui TTS의 시스템 볼륨 조절 기능을 확인하세요")
            print("   - PulseAudio 또는 ALSA 설정을 확인하세요")
        
    except ImportError as e:
        print(f"❌ 임포트 오류: {e}")
        print("필요한 모듈이 설치되지 않았습니다.")
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_volume_control() 