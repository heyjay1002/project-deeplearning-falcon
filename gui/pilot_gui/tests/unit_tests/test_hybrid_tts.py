#!/usr/bin/env python3
"""
하이브리드 TTS 엔진 볼륨 조절 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui/pilot_gui'))

def test_hybrid_tts_volume():
    """하이브리드 TTS 볼륨 테스트"""
    print("🔀 하이브리드 TTS 볼륨 조절 테스트")
    print("=" * 40)
    
    try:
        from tts.hybrid_tts_engine import HybridTTSEngine
        
        print("1️⃣ 하이브리드 TTS 엔진 초기화...")
        # Coqui를 시도하되 실패하면 pyttsx3 사용
        hybrid_tts = HybridTTSEngine(
            use_coqui=True,
            coqui_model="tts_models/en/ljspeech/tacotron2-DDC",
            fallback_to_pyttsx3=True
        )
        
        if not hybrid_tts.is_engine_ready():
            print("❌ 하이브리드 TTS 엔진이 준비되지 않음")
            return False
        
        print(f"✅ 하이브리드 TTS 엔진 준비 완료")
        print(f"   현재 엔진: {hybrid_tts.get_current_engine()}")
        print(f"   상태: {hybrid_tts.get_status()}")
        
        # 볼륨 테스트 시퀀스
        volume_tests = [
            (1.0, "100% 볼륨 테스트"),
            (0.5, "50% 볼륨 테스트"), 
            (0.0, "음소거 테스트 (소리 안남)"),
            (0.8, "80% 볼륨 복원 테스트")
        ]
        
        for volume, description in volume_tests:
            print(f"\n🔊 {description}...")
            
            # 볼륨 설정
            hybrid_tts.set_volume(volume)
            current_volume = hybrid_tts.get_current_volume()
            print(f"   설정된 볼륨: {current_volume:.2f}")
            
            # 음성 재생
            test_text = f"Hybrid TTS volume test at {int(volume*100)} percent"
            hybrid_tts.speak(test_text, blocking=True)
            
            if volume == 0.0:
                print("   (위 텍스트는 소리가 안 나야 정상)")
        
        print("\n✅ 하이브리드 TTS 볼륨 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 하이브리드 TTS 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_tts_scenario():
    """GUI와 같은 시나리오로 TTS 테스트"""
    print("\n🖥️ GUI 시나리오 재현 테스트")
    print("=" * 40)
    
    try:
        # GUI에서 사용하는 것과 동일한 설정
        from controller.voice_interaction_controller import create_voice_controller_with_structured_query
        
        print("1️⃣ 음성 상호작용 컨트롤러 초기화...")
        controller = create_voice_controller_with_structured_query(
            server_url="http://localhost:8000",
            use_mock_fallback=True,
            stt_model="small"
        )
        
        if not controller or not hasattr(controller, 'tts_engine'):
            print("❌ 컨트롤러 또는 TTS 엔진이 없음")
            return False
        
        print("✅ 컨트롤러 초기화 완료")
        print(f"   TTS 엔진 타입: {type(controller.tts_engine).__name__}")
        
        # GUI와 동일한 방식으로 볼륨 조절
        volume_levels = [100, 50, 0, 50]  # SPK VOLUME 슬라이더 값
        
        for volume_percent in volume_levels:
            print(f"\n🎚️ SPK VOLUME 슬라이더: {volume_percent}%")
            
            # GUI와 동일한 볼륨 설정 방식
            volume_normalized = volume_percent / 100.0
            
            if hasattr(controller.tts_engine, 'set_volume'):
                controller.tts_engine.set_volume(volume_normalized)
                current_volume = controller.tts_engine.get_current_volume()
                print(f"   설정된 볼륨: {current_volume:.2f}")
                
                # 음성 재생
                test_text = f"GUI volume test at {volume_percent} percent"
                if hasattr(controller.tts_engine, 'speak'):
                    controller.tts_engine.speak(test_text, blocking=True)
                else:
                    controller._process_tts(test_text)
                
                if volume_percent == 0:
                    print("   (음소거 상태 - 소리 안남)")
            else:
                print("   ⚠️ TTS 엔진에 볼륨 조절 기능이 없음")
        
        print("\n✅ GUI 시나리오 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ GUI 시나리오 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print("🎧 SPK VOLUME 50% 소리 안남 문제 해결 테스트")
    print("=" * 50)
    
    # 1. 하이브리드 TTS 직접 테스트
    hybrid_ok = test_hybrid_tts_volume()
    
    # 2. GUI 시나리오 재현 테스트
    gui_ok = test_gui_tts_scenario()
    
    print("\n📋 최종 결과:")
    if hybrid_ok and gui_ok:
        print("✅ 모든 테스트 통과! SPK VOLUME 슬라이더가 정상 작동해야 합니다")
        print("\n🔧 GUI에서 여전히 문제가 있다면:")
        print("   1. GUI를 다시 시작하세요")
        print("   2. SPK VOLUME 슬라이더를 100%로 올린 후 다시 50%로 설정하세요")
        print("   3. 음성 테스트 버튼을 눌러보세요")
    elif hybrid_ok and not gui_ok:
        print("✅ 하이브리드 TTS는 정상, GUI 연동에 문제")
    elif not hybrid_ok:
        print("❌ 하이브리드 TTS 자체에 문제")
    
    print("\n💡 참고:")
    print("   - Coqui TTS 오류로 인해 pyttsx3로 자동 전환됩니다")
    print("   - pyttsx3 엔진은 볼륨 조절이 정상 작동합니다")

if __name__ == "__main__":
    main() 