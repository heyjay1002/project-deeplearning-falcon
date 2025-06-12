#!/usr/bin/env python3
"""
표준 응답 테이블 테스트 스크립트
Confluence 문서의 RESPONSE_TYPE 테이블 기반 응답 생성 확인
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui', 'pilot_gui'))

from request_router.response_processor import ResponseProcessor

def test_standard_responses():
    """Confluence 문서 기준 표준 응답 테이블 테스트"""
    print("🧪 Confluence 문서 기준 표준 응답 테이블 테스트 시작")
    print("=" * 60)
    
    # ResponseProcessor 초기화
    processor = ResponseProcessor()
    
    # Confluence 문서 기준 테스트 케이스들
    test_cases = [
        # 조류 위험도 응답 - Confluence 문서 기준
        {
            "name": "조류 위험도 높음",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "bird_risk_inquiry",
                "response_code": "BIRD_RISK_HIGH",
                "source": "main_server"
            },
            "original_request": {"callsign": "KAL123"}
        },
        {
            "name": "조류 위험도 보통",
            "response_data": {
                "type": "response",
                "status": "success", 
                "intent": "bird_risk_inquiry",
                "response_code": "BIRD_RISK_MEDIUM",
                "source": "main_server"
            },
            "original_request": {"callsign": "AAR456"}
        },
        {
            "name": "조류 위험도 낮음",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "bird_risk_inquiry", 
                "response_code": "BIRD_RISK_LOW",
                "source": "main_server"
            },
            "original_request": {"callsign": "UAL789"}
        },
        
        # 활주로 상태 응답 - Confluence 문서 기준
        {
            "name": "활주로 A 사용 가능",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "runway_alpha_status",
                "response_code": "RWY_A_CLEAR",
                "source": "main_server"
            },
            "original_request": {"callsign": "DLH100"}
        },
        {
            "name": "활주로 A 차단됨",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "runway_alpha_status",
                "response_code": "RWY_A_BLOCKED",
                "source": "main_server"
            },
            "original_request": {"callsign": "SWA200"}
        },
        {
            "name": "활주로 B 사용 가능",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "runway_bravo_status",
                "response_code": "RWY_B_CLEAR",
                "source": "main_server"
            },
            "original_request": {"callsign": "AFR300"}
        },
        {
            "name": "활주로 B 차단됨",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "runway_bravo_status",
                "response_code": "RWY_B_BLOCKED",
                "source": "main_server"
            },
            "original_request": {"callsign": "BAW400"}
        },
        
        # 사용 가능한 활주로 응답 - Confluence 문서 기준
        {
            "name": "모든 활주로 사용 가능",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "available_runway_inquiry",
                "response_code": "AVAILABLE_RUNWAYS_ALL",
                "source": "main_server"
            },
            "original_request": {"callsign": "JAL500"}
        },
        {
            "name": "활주로 A만 사용 가능",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "available_runway_inquiry",
                "response_code": "AVAILABLE_RUNWAYS_A_ONLY",
                "source": "main_server"
            },
            "original_request": {"callsign": "ANA600"}
        },
        {
            "name": "활주로 B만 사용 가능",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "available_runway_inquiry",
                "response_code": "AVAILABLE_RUNWAYS_B_ONLY",
                "source": "main_server"
            },
            "original_request": {"callsign": "EVA700"}
        },
        {
            "name": "사용 가능한 활주로 없음",
            "response_data": {
                "type": "response",
                "status": "success",
                "intent": "available_runway_inquiry",
                "response_code": "NO_RUNWAYS_AVAILABLE",
                "source": "main_server"
            },
            "original_request": {"callsign": "CPA800"}
        },
        
        # 오류 응답 - Confluence 문서 기준
        {
            "name": "인식 실패",
            "response_data": {
                "type": "response",
                "status": "error",
                "intent": "unknown",
                "response_code": "UNRECOGNIZED_COMMAND",
                "source": "main_server"
            },
            "original_request": {"callsign": "TEST001"}
        }
    ]
    
    # 테스트 실행
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        try:
            success, response_text = processor.process_response(
                test_case["response_data"], 
                test_case["original_request"]
            )
            
            print(f"   콜사인: {test_case['original_request']['callsign']}")
            print(f"   응답코드: {test_case['response_data']['response_code']}")
            print(f"   성공여부: {success}")
            print(f"   응답텍스트: '{response_text}'")
            
            if success:
                success_count += 1
            
            # 응답 검증
            expected_callsign = test_case['original_request']['callsign']
            if expected_callsign in response_text:
                print("   ✅ 콜사인 포함됨")
            else:
                print("   ⚠️ 콜사인 누락")
                
        except Exception as e:
            print(f"   ❌ 테스트 오류: {e}")
    
    print(f"\n📈 테스트 결과: {success_count}/{len(test_cases)} 성공")
    
    if success_count == len(test_cases):
        print("✅ 모든 표준 응답 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")
    
    return success_count == len(test_cases)

def test_unknown_response_code():
    """알 수 없는 응답 코드 테스트"""
    print("\n🔍 알 수 없는 응답 코드 테스트")
    print("-" * 40)
    
    processor = ResponseProcessor()
    
    # 존재하지 않는 응답 코드
    response_data = {
        "type": "response",
        "status": "success",
        "intent": "test",
        "response_code": "UNKNOWN_CODE_123",
        "source": "main_server"
    }
    
    original_request = {"callsign": "TEST001"}
    
    success, response_text = processor.process_response(response_data, original_request)
    
    print(f"성공: {success}")
    print(f"응답: '{response_text}'")
    print("예상: UNRECOGNIZED_COMMAND 응답으로 폴백")

def test_confluence_message_validation():
    """Confluence 문서 기준 메시지 검증 테스트"""
    print("\n🔒 Confluence 문서 기준 메시지 검증 테스트")
    print("-" * 40)
    
    processor = ResponseProcessor()
    
    # 유효한 메시지들
    valid_messages = [
        {
            "type": "response",
            "status": "success",
            "intent": "bird_risk_inquiry",
            "response_code": "BIRD_RISK_HIGH",
            "source": "main_server"
        },
        {
            "type": "response",
            "status": "error",
            "intent": "unknown",
            "response_code": "UNRECOGNIZED_COMMAND",
            "source": "main_server"
        }
    ]
    
    # 무효한 메시지들
    invalid_messages = [
        {"invalid": "message"},  # type 없음
        {"type": "response"},  # status 없음
        {"type": "response", "status": "success"},  # response_code 없음
        {"type": "response", "status": "error"}  # response_code 없음
    ]
    
    print("유효한 메시지 검증:")
    for i, msg in enumerate(valid_messages, 1):
        is_valid, message = processor.validate_response_data(msg)
        print(f"  {i}. {is_valid} - {message}")
    
    print("\n무효한 메시지 검증:")
    for i, msg in enumerate(invalid_messages, 1):
        is_valid, message = processor.validate_response_data(msg)
        print(f"  {i}. {is_valid} - {message}")

if __name__ == "__main__":
    print("🚁 Confluence 문서 기준 표준 응답 테스트 시작")
    print("=" * 60)
    
    # 메인 테스트 실행
    all_passed = test_standard_responses()
    
    # 추가 테스트들
    test_unknown_response_code()
    test_confluence_message_validation()
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 모든 테스트 통과! Confluence 문서 기준 호환성 확인됨")
    else:
        print("⚠️ 일부 테스트 실패 - 표준 응답 테이블 점검 필요")
    
    print("테스트 완료!") 