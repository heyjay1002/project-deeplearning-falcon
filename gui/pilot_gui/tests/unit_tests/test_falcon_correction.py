#!/usr/bin/env python3
"""
FALCON 콜사인 오인식 보정 테스트
- 실제 발견된 balcony → falcon 오인식 케이스 테스트
- 콜사인 추출 및 분류 정확도 검증
"""

import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from query_parser.request_classifier import RequestClassifier

def test_falcon_callsign_correction():
    """FALCON 콜사인 오인식 보정 테스트"""
    classifier = RequestClassifier()
    
    # 실제 발견된 오인식 케이스들
    test_cases = [
        # (STT 오인식 결과, 예상 분류, 설명)
        ("balcony 123, run a status check", "AVAILABLE_RUNWAY_INQUIRY", "balcony → falcon"),
        ("balcony 456, bird risk assessment", "BIRD_RISK_INQUIRY", "balcony → falcon"),
        ("balcon 789, runway alpha status", "RUNWAY_ALPHA_STATUS", "balcon → falcon"),
        ("falkon 321, runway bravo check", "RUNWAY_BRAVO_STATUS", "falkon → falcon"),
        ("falco 555, available runway report", "AVAILABLE_RUNWAY_INQUIRY", "falco → falcon"),
    ]
    
    print("✈️ FALCON 콜사인 오인식 보정 테스트:")
    success_count = 0
    
    for i, (stt_text, expected, description) in enumerate(test_cases, 1):
        request_code, params = classifier.classify(stt_text)
        is_success = request_code == expected
        
        if is_success:
            success_count += 1
        
        print(f"\n  {i}. {description}")
        print(f"     STT 입력: '{stt_text}'")
        if 'corrected_text' in params and params['corrected_text']:
            print(f"     보정 결과: '{params['corrected_text']}'")
        print(f"     분류 결과: {request_code} {'✅' if is_success else '❌'}")
        if 'callsign' in params:
            print(f"     콜사인: {params['callsign']}")
        print(f"     신뢰도: {params.get('confidence_score', 0)}")
    
    accuracy = success_count / len(test_cases) * 100
    print(f"\n📊 FALCON 콜사인 보정 정확도: {success_count}/{len(test_cases)} ({accuracy:.1f}%)")
    return accuracy

def test_real_balcony_case():
    """실제 발견된 balcony 케이스 테스트"""
    classifier = RequestClassifier()
    
    # 실제 로그에서 발견된 케이스
    real_case = "balcony 123, run a status check"
    
    print("🎯 실제 balcony 오인식 케이스 테스트:")
    print(f"실제 발화 추정: 'FALCON 123, runway status check'")
    print(f"STT 결과: '{real_case}'")
    
    request_code, params = classifier.classify(real_case)
    
    print(f"\n보정 과정:")
    if 'corrected_text' in params and params['corrected_text']:
        print(f"  보정 결과: '{params['corrected_text']}'")
    else:
        print(f"  보정 없음")
    
    print(f"\n최종 결과:")
    print(f"  분류: {request_code}")
    if 'callsign' in params:
        print(f"  콜사인: {params['callsign']}")
    else:
        print(f"  콜사인: 추출 실패")
    print(f"  신뢰도: {params.get('confidence_score', 0)}")
    print(f"  매칭 키워드: {params.get('matched_keywords', [])}")
    
    # 콜사인 추출 성공 여부 확인
    callsign_success = 'callsign' in params and 'FALCON' in params['callsign'].upper()
    classification_success = request_code != "UNKNOWN_REQUEST"
    
    return callsign_success, classification_success

def test_callsign_extraction_improvement():
    """콜사인 추출 개선 효과 테스트"""
    print("📈 콜사인 추출 개선 효과:")
    
    # 보정 기능 비활성화를 위한 임시 클래스
    class NoCorrectClassifier(RequestClassifier):
        def _correct_stt_errors(self, text):
            return text.lower()  # 보정 없이 소문자 변환만
    
    original_classifier = RequestClassifier()
    no_correct_classifier = NoCorrectClassifier()
    
    # 콜사인 오인식 테스트 케이스들
    test_cases = [
        "balcony 123, bird risk assessment",
        "balcon 456, runway alpha status",
        "falkon 789, available runway report",
        "falco 321, runway bravo check",
    ]
    
    original_callsign_success = 0
    no_correct_callsign_success = 0
    
    for stt_text in test_cases:
        # 보정 있음
        _, params1 = original_classifier.classify(stt_text)
        if 'callsign' in params1 and 'FALCON' in params1['callsign'].upper():
            original_callsign_success += 1
        
        # 보정 없음
        _, params2 = no_correct_classifier.classify(stt_text)
        if 'callsign' in params2 and 'FALCON' in params2['callsign'].upper():
            no_correct_callsign_success += 1
    
    total = len(test_cases)
    original_rate = original_callsign_success / total * 100
    no_correct_rate = no_correct_callsign_success / total * 100
    improvement = original_rate - no_correct_rate
    
    print(f"  보정 없음: {no_correct_callsign_success}/{total} ({no_correct_rate:.1f}%)")
    print(f"  보정 있음: {original_callsign_success}/{total} ({original_rate:.1f}%)")
    print(f"  개선도: +{improvement:.1f}%p")
    
    return improvement

def main():
    """메인 함수"""
    print("=== FALCON 콜사인 오인식 보정 테스트 ===\n")
    
    # 개별 테스트
    falcon_accuracy = test_falcon_callsign_correction()
    print()
    callsign_success, classification_success = test_real_balcony_case()
    print()
    callsign_improvement = test_callsign_extraction_improvement()
    
    # 전체 결과 요약
    print(f"\n{'='*60}")
    print(f"📊 FALCON 콜사인 보정 결과 요약:")
    print(f"  ✈️ FALCON 콜사인 보정 정확도: {falcon_accuracy:.1f}%")
    print(f"  🎯 실제 케이스 콜사인 추출: {'성공' if callsign_success else '실패'}")
    print(f"  🎯 실제 케이스 분류: {'성공' if classification_success else '실패'}")
    print(f"  📈 콜사인 추출 개선: +{callsign_improvement:.1f}%p")
    
    # 종합 평가
    if falcon_accuracy >= 80 and callsign_success and classification_success:
        print(f"\n🎉 FALCON 콜사인 보정 성공!")
    elif falcon_accuracy >= 60:
        print(f"\n⚠️ FALCON 콜사인 보정 개선 필요")
    else:
        print(f"\n❌ FALCON 콜사인 보정 실패")

if __name__ == "__main__":
    main() 