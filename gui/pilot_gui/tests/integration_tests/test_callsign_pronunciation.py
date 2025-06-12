#!/usr/bin/env python3
"""
콜사인 발음 테스트 스크립트
"""

import sys
import os
sys.path.append('gui/pilot_gui')

def test_callsign_pronunciation():
    """콜사인 발음 변환 테스트"""
    print("✈️ 콜사인 발음 변환 테스트")
    print("=" * 50)
    
    try:
        from request_router.response_processor import ResponseProcessor
        
        processor = ResponseProcessor()
        
        # 테스트 케이스들 (콜사인 + 숫자)
        test_cases = [
            # 한국 항공사
            ("KAL2172, Runway Alpha is clear.", "Korean Air two one seven two, Runway Alpha is clear."),
            ("AAR8940, Cleared to land, Runway Bravo.", "Asiana eight nine four zero, Cleared to land, Runway Bravo."),
            ("JJA4161, Bird activity reported.", "Jeju Air four one six one, Bird activity reported."),
            ("LJ6476, Hold position.", "Jin Air six four seven six, Hold position."),
            ("RS765, Proceed as requested.", "Air Seoul seven six five, Proceed as requested."),
            ("B5173, Runway condition unsafe.", "Air Busan five one seven three, Runway condition unsafe."),
            
            # 한국 민간/공군
            ("HL9233, Cleared to land.", "Hotel Lima niner two three three, Cleared to land."),
            ("ROKAF63, Runway Alpha clear.", "Rokaf six three, Runway Alpha clear."),
            
            # 미국 등록기
            ("N430XM, Bird activity minimal.", "November four three zero X-ray Mike, Bird activity minimal."),
            
            # 테스트용 (FALCON)
            ("FALCON123, Runway Alpha is clear.", "Falcon one two three, Runway Alpha is clear."),
            
            # 알려지지 않은 콜사인 (NATO 음성 문자로 변환)
            ("XYZ456, Hold position.", "X-ray Yankee Zulu four five six, Hold position.")
        ]
        
        print("🔍 콜사인 발음 변환 결과:")
        print("-" * 80)
        
        for i, (input_text, expected_output) in enumerate(test_cases, 1):
            # 숫자 변환 함수 직접 테스트
            converted = processor._convert_aviation_numbers(input_text)
            
            print(f"테스트 {i:2d}:")
            print(f"  입력:   {input_text}")
            print(f"  결과:   {converted}")
            print(f"  예상:   {expected_output}")
            
            # 결과 확인
            if converted == expected_output:
                print(f"  상태:   ✅ 성공")
            else:
                print(f"  상태:   ❌ 실패")
            print()
        
        print("🎯 콜사인 발음 규칙:")
        print("  • 콜사인 부분: 항공사명으로 변환 (KAL → Korean Air)")
        print("  • 숫자 부분: 개별 숫자로 변환 (123 → one two three)")
        print("  • 9는 'niner'로 발음")
        print("  • 알려지지 않은 콜사인은 NATO 음성 문자로 변환")
        
    except ImportError as e:
        print(f"❌ 임포트 오류: {e}")
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

def test_tts_with_callsigns():
    """실제 TTS로 콜사인 발음 테스트"""
    print("\n🎵 TTS 콜사인 발음 테스트")
    print("=" * 50)
    
    try:
        from tts.coqui_tts_engine import CoquiTTSEngine
        from request_router.response_processor import ResponseProcessor
        
        # TTS 엔진 초기화
        tts_engine = CoquiTTSEngine()
        processor = ResponseProcessor()
        
        if tts_engine.is_engine_ready():
            print("✅ TTS 엔진 준비 완료!")
            
            # 테스트 음성들
            test_texts = [
                "FALCON123, Runway Alpha is clear. Proceed as requested.",
                "KAL2172, Cleared to land, Runway Bravo.",
                "AAR8940, Bird activity reported. Use caution.",
                "HL9233, Hold position. Runway condition unsafe."
            ]
            
            for i, original_text in enumerate(test_texts, 1):
                # 콜사인 변환
                converted_text = processor._convert_aviation_numbers(original_text)
                
                print(f"\n🎵 테스트 {i}:")
                print(f"  원본: {original_text}")
                print(f"  변환: {converted_text}")
                print("  (콜사인이 올바르게 발음되는지 확인하세요)")
                
                # TTS로 음성 생성
                tts_engine.speak(converted_text, blocking=True)
                print(f"✅ 테스트 {i} 완료!")
                
                # 다음 테스트 전 잠시 대기
                import time
                time.sleep(1)
            
            print("\n🎯 콜사인 발음이 올바른지 확인하세요!")
            print("  • FALCON → 'Falcon' (자연스러운 발음)")
            print("  • KAL → 'Korean Air'")
            print("  • 숫자는 개별 발음 (123 → 'one two three')")
            print("  • ROKAF → 'Rokaf' (자연스러운 발음)")
            
        else:
            print("❌ TTS 엔진이 준비되지 않음")
            
    except ImportError as e:
        print(f"❌ 임포트 오류: {e}")
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("✈️ 콜사인 발음 시스템 테스트")
    print("=" * 60)
    print("🔍 확인 사항:")
    print("  1. FALCON이 '팔콘'으로 발음되는지 (F-A-L-C-O-N 아님)")
    print("  2. KAL이 'Korean Air'로 발음되는지")
    print("  3. 숫자는 개별 숫자로 발음되는지 (123 → one two three)")
    print("=" * 60)
    
    # 1. 콜사인 변환 로직 테스트
    test_callsign_pronunciation()
    
    # 2. 실제 TTS 발음 테스트
    test_tts_with_callsigns()
    
    print("\n🏁 모든 테스트 완료!")
    print("💡 콜사인이 올바르게 발음된다면 성공입니다!") 