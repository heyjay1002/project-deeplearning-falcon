#!/usr/bin/env python3
"""
항공 통신 숫자 변환 테스트 스크립트
"""

import sys
import os
sys.path.append('gui/pilot_gui')

def test_number_conversion():
    """숫자 변환 기능 테스트"""
    print("🔢 항공 통신 숫자 변환 테스트")
    print("=" * 50)
    
    try:
        from request_router.response_processor import ResponseProcessor
        
        processor = ResponseProcessor()
        
        # 테스트 케이스들
        test_cases = [
            "FALCON 123, Runway Alpha is clear.",
            "KAL 456, Cleared to land, Runway Bravo.",
            "AAR 789, Bird activity reported.",
            "Flight 1234, Hold position.",
            "Aircraft 007, Proceed as requested.",
            "BAW 999, Runway condition unsafe.",
            "No numbers here",
            "Mixed 123 and 456 numbers",
            "Single digit 5 test"
        ]
        
        print("📝 테스트 케이스:")
        for i, test_text in enumerate(test_cases, 1):
            converted = processor._convert_numbers_to_aviation_format(test_text)
            print(f"{i:2d}. 원본: '{test_text}'")
            print(f"    변환: '{converted}'")
            print()
        
        print("✅ 숫자 변환 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

def test_full_response_processing():
    """전체 응답 처리 테스트"""
    print("\n🎯 전체 응답 처리 테스트")
    print("=" * 50)
    
    try:
        from request_router.response_processor import ResponseProcessor
        
        processor = ResponseProcessor()
        
        # 모의 응답 데이터
        test_responses = [
            {
                "type": "response",
                "intent": "runway_status",
                "result": {
                    "response_code": "RWY_A_CLEAR"
                }
            },
            {
                "type": "response", 
                "intent": "landing_clearance",
                "result": {
                    "response_code": "CLEARED_TO_LAND_RWY_B"
                }
            }
        ]
        
        # 모의 요청 데이터
        test_requests = [
            {"callsign": "FALCON 123"},
            {"callsign": "KAL 456"}
        ]
        
        print("📝 전체 처리 테스트:")
        for i, (response_data, request_data) in enumerate(zip(test_responses, test_requests), 1):
            success, final_text = processor.process_response(response_data, request_data)
            print(f"{i}. 콜사인: {request_data['callsign']}")
            print(f"   응답코드: {response_data['result']['response_code']}")
            print(f"   성공여부: {success}")
            print(f"   최종응답: '{final_text}'")
            print()
        
        print("✅ 전체 응답 처리 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_number_conversion()
    test_full_response_processing() 