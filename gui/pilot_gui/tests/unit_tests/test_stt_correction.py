#!/usr/bin/env python3
"""
STT 오인식 보정 기능 테스트
- 실제 STT 오인식 케이스 테스트
- 보정 전후 분류 정확도 비교
- 항공 용어 특화 보정 검증
"""

import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from query_parser.request_classifier import RequestClassifier

def test_bird_misrecognition():
    """조류(bird) 관련 오인식 보정 테스트"""
    classifier = RequestClassifier()
    
    # 실제 STT 오인식 케이스들
    test_cases = [
        # (STT 오인식 결과, 예상 분류, 설명)
        ("FALCON 789, bolt activity check", "BIRD_RISK_INQUIRY", "bolt → bird"),
        ("FALCON 123, board risk assessment", "BIRD_RISK_INQUIRY", "board → bird"),
        ("FALCON 456, both hazard report", "BIRD_RISK_INQUIRY", "both → bird"),
        ("FALCON 321, birth activity status", "BIRD_RISK_INQUIRY", "birth → bird"),
        ("FALCON 555, bert strike warning", "BIRD_RISK_INQUIRY", "bert → bird"),
    ]
    
    print("🐦 조류(bird) 오인식 보정 테스트:")
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
    print(f"\n📊 조류 오인식 보정 정확도: {success_count}/{len(test_cases)} ({accuracy:.1f}%)")
    return accuracy

def test_runway_misrecognition():
    """활주로(runway) 관련 오인식 보정 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        ("FALCON 123, run way alpha status check", "RUNWAY_ALPHA_STATUS", "run way → runway"),
        ("FALCON 456, runaway bravo condition", "RUNWAY_BRAVO_STATUS", "runaway → runway"),
        ("FALCON 789, runway alfa hazard assessment", "RUNWAY_ALPHA_STATUS", "alfa → alpha"),
        ("FALCON 321, runway brabo status check", "RUNWAY_BRAVO_STATUS", "brabo → bravo"),
        ("FALCON 555, run-way alpha condition report", "RUNWAY_ALPHA_STATUS", "run-way → runway"),
    ]
    
    print("🛬 활주로(runway) 오인식 보정 테스트:")
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
        if 'runway' in params:
            print(f"     활주로: {params['runway']}")
        print(f"     신뢰도: {params.get('confidence_score', 0)}")
    
    accuracy = success_count / len(test_cases) * 100
    print(f"\n📊 활주로 오인식 보정 정확도: {success_count}/{len(test_cases)} ({accuracy:.1f}%)")
    return accuracy

def test_complex_misrecognition():
    """복합 오인식 보정 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        ("FALCON 123, bolt acticity chuck", "BIRD_RISK_INQUIRY", "bolt→bird, acticity→activity, chuck→check"),
        ("FALCON 456, run way alfa states chuck", "RUNWAY_ALPHA_STATUS", "run way→runway, alfa→alpha, states→status, chuck→check"),
        ("FALCON 789, availabe run way reprot", "AVAILABLE_RUNWAY_INQUIRY", "availabe→available, run way→runway, reprot→report"),
        ("FALCON 321, runway brabo condtion assessement", "RUNWAY_BRAVO_STATUS", "brabo→bravo, condtion→condition, assessement→assessment"),
    ]
    
    print("🔧 복합 오인식 보정 테스트:")
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
    print(f"\n📊 복합 오인식 보정 정확도: {success_count}/{len(test_cases)} ({accuracy:.1f}%)")
    return accuracy

def test_real_stt_case():
    """실제 STT 오인식 케이스 테스트 (사용자 로그 기반)"""
    classifier = RequestClassifier()
    
    # 사용자가 제공한 실제 오인식 케이스
    real_case = "FALCON 789, bolt activity check."
    expected = "BIRD_RISK_INQUIRY"
    
    print("🎯 실제 STT 오인식 케이스 테스트:")
    print(f"실제 발화: 'FALCON 789, bird activity check'")
    print(f"STT 결과: '{real_case}'")
    
    request_code, params = classifier.classify(real_case)
    is_success = request_code == expected
    
    print(f"\n보정 과정:")
    if 'corrected_text' in params and params['corrected_text']:
        print(f"  보정 결과: '{params['corrected_text']}'")
    else:
        print(f"  보정 없음")
    
    print(f"\n최종 결과:")
    print(f"  분류: {request_code} {'✅' if is_success else '❌'}")
    if 'callsign' in params:
        print(f"  콜사인: {params['callsign']}")
    print(f"  신뢰도: {params.get('confidence_score', 0)}")
    print(f"  매칭 키워드: {params.get('matched_keywords', [])}")
    
    return is_success

def test_correction_performance():
    """보정 전후 성능 비교"""
    print("📈 보정 전후 성능 비교:")
    
    # 보정 기능 비활성화를 위한 임시 클래스
    class NoCorrectClassifier(RequestClassifier):
        def _correct_stt_errors(self, text):
            return text.lower()  # 보정 없이 소문자 변환만
    
    original_classifier = RequestClassifier()
    no_correct_classifier = NoCorrectClassifier()
    
    # 오인식 테스트 케이스들
    test_cases = [
        ("FALCON 123, bolt activity check", "BIRD_RISK_INQUIRY"),
        ("FALCON 456, board risk assessment", "BIRD_RISK_INQUIRY"),
        ("FALCON 789, run way alpha status", "RUNWAY_ALPHA_STATUS"),
        ("FALCON 321, runway brabo condition", "RUNWAY_BRAVO_STATUS"),
        ("FALCON 555, availabe runway reprot", "AVAILABLE_RUNWAY_INQUIRY"),
    ]
    
    original_correct = 0
    no_correct_correct = 0
    
    for stt_text, expected in test_cases:
        # 보정 있음
        result1, _ = original_classifier.classify(stt_text)
        if result1 == expected:
            original_correct += 1
        
        # 보정 없음
        result2, _ = no_correct_classifier.classify(stt_text)
        if result2 == expected:
            no_correct_correct += 1
    
    total = len(test_cases)
    original_accuracy = original_correct / total * 100
    no_correct_accuracy = no_correct_correct / total * 100
    improvement = original_accuracy - no_correct_accuracy
    
    print(f"  보정 없음: {no_correct_correct}/{total} ({no_correct_accuracy:.1f}%)")
    print(f"  보정 있음: {original_correct}/{total} ({original_accuracy:.1f}%)")
    print(f"  개선도: +{improvement:.1f}%p")
    
    return improvement

def main():
    """메인 함수"""
    print("=== STT 오인식 보정 기능 테스트 ===\n")
    
    # 개별 테스트
    bird_accuracy = test_bird_misrecognition()
    print()
    runway_accuracy = test_runway_misrecognition()
    print()
    complex_accuracy = test_complex_misrecognition()
    print()
    real_case_success = test_real_stt_case()
    print()
    improvement = test_correction_performance()
    
    # 전체 결과 요약
    print(f"\n{'='*60}")
    print(f"📊 전체 테스트 결과 요약:")
    print(f"  🐦 조류 오인식 보정: {bird_accuracy:.1f}%")
    print(f"  🛬 활주로 오인식 보정: {runway_accuracy:.1f}%")
    print(f"  🔧 복합 오인식 보정: {complex_accuracy:.1f}%")
    print(f"  🎯 실제 케이스 보정: {'성공' if real_case_success else '실패'}")
    print(f"  📈 전체 성능 개선: +{improvement:.1f}%p")
    
    # 종합 평가
    avg_accuracy = (bird_accuracy + runway_accuracy + complex_accuracy) / 3
    if avg_accuracy >= 90 and improvement >= 50:
        print(f"\n🎉 보정 기능 성공! 평균 정확도: {avg_accuracy:.1f}%")
    elif avg_accuracy >= 70:
        print(f"\n⚠️ 보정 기능 개선 필요. 평균 정확도: {avg_accuracy:.1f}%")
    else:
        print(f"\n❌ 보정 기능 실패. 평균 정확도: {avg_accuracy:.1f}%")

if __name__ == "__main__":
    main() 