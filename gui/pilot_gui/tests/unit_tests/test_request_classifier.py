#!/usr/bin/env python3
"""
RequestClassifier 단위 테스트
- 4개 카테고리 분류 정확도 테스트
- 키워드 매칭 테스트
- 콜사인 및 활주로 정보 추출 테스트
"""

import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from query_parser.request_classifier import RequestClassifier

def test_bird_risk_inquiry():
    """조류 위험도 문의 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        "FALCON 123, bird risk assessment",
        "FALCON 456, requesting bird hazard report", 
        "FALCON 789, bird activity status check",
        "FALCON 321, wildlife hazard assessment"
    ]
    
    print("🐦 조류 위험도 문의 테스트:")
    for i, text in enumerate(test_cases, 1):
        request_code, params = classifier.classify(text)
        success = request_code == "BIRD_RISK_INQUIRY"
        print(f"  {i}. '{text}'")
        print(f"     결과: {request_code} {'✅' if success else '❌'}")
        if 'callsign' in params:
            print(f"     콜사인: {params['callsign']}")
        print(f"     점수: {params.get('confidence_score', 0)}")
        print()

def test_runway_alpha_status():
    """런웨이 A 상태 문의 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        "FALCON 123, runway Alpha status check",
        "FALCON 456, runway A condition report",
        "FALCON 789, runway Alpha hazard assessment", 
        "FALCON 321, requesting runway A safety status"
    ]
    
    print("🛬 런웨이 A 상태 문의 테스트:")
    for i, text in enumerate(test_cases, 1):
        request_code, params = classifier.classify(text)
        success = request_code == "RUNWAY_ALPHA_STATUS"
        print(f"  {i}. '{text}'")
        print(f"     결과: {request_code} {'✅' if success else '❌'}")
        if 'callsign' in params:
            print(f"     콜사인: {params['callsign']}")
        if 'runway' in params:
            print(f"     활주로: {params['runway']}")
        print(f"     점수: {params.get('confidence_score', 0)}")
        print()

def test_runway_bravo_status():
    """런웨이 B 상태 문의 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        "FALCON 123, runway Bravo status check",
        "FALCON 456, runway B condition report",
        "FALCON 789, runway Bravo hazard assessment",
        "FALCON 321, requesting runway B safety status"
    ]
    
    print("🛬 런웨이 B 상태 문의 테스트:")
    for i, text in enumerate(test_cases, 1):
        request_code, params = classifier.classify(text)
        success = request_code == "RUNWAY_BRAVO_STATUS"
        print(f"  {i}. '{text}'")
        print(f"     결과: {request_code} {'✅' if success else '❌'}")
        if 'callsign' in params:
            print(f"     콜사인: {params['callsign']}")
        if 'runway' in params:
            print(f"     활주로: {params['runway']}")
        print(f"     점수: {params.get('confidence_score', 0)}")
        print()

def test_available_runway_inquiry():
    """사용 가능한 런웨이 문의 테스트"""
    classifier = RequestClassifier()
    
    test_cases = [
        "FALCON 123, available runway status",
        "FALCON 456, requesting active runway information",
        "FALCON 789, which runway is available",
        "FALCON 321, runway availability check"
    ]
    
    print("✈️ 사용 가능한 런웨이 문의 테스트:")
    for i, text in enumerate(test_cases, 1):
        request_code, params = classifier.classify(text)
        success = request_code == "AVAILABLE_RUNWAY_INQUIRY"
        print(f"  {i}. '{text}'")
        print(f"     결과: {request_code} {'✅' if success else '❌'}")
        if 'callsign' in params:
            print(f"     콜사인: {params['callsign']}")
        print(f"     점수: {params.get('confidence_score', 0)}")
        print()

def test_classification_accuracy():
    """전체 분류 정확도 테스트"""
    classifier = RequestClassifier()
    
    # 각 카테고리별 테스트 케이스
    test_data = [
        # 조류 위험도 문의
        ("FALCON 123, bird risk assessment", "BIRD_RISK_INQUIRY"),
        ("FALCON 456, requesting bird hazard report", "BIRD_RISK_INQUIRY"),
        ("FALCON 789, bird activity status check", "BIRD_RISK_INQUIRY"),
        ("FALCON 321, wildlife hazard assessment", "BIRD_RISK_INQUIRY"),
        
        # 런웨이 A 상태 문의
        ("FALCON 123, runway Alpha status check", "RUNWAY_ALPHA_STATUS"),
        ("FALCON 456, runway A condition report", "RUNWAY_ALPHA_STATUS"),
        ("FALCON 789, runway Alpha hazard assessment", "RUNWAY_ALPHA_STATUS"),
        ("FALCON 321, requesting runway A safety status", "RUNWAY_ALPHA_STATUS"),
        
        # 런웨이 B 상태 문의
        ("FALCON 123, runway Bravo status check", "RUNWAY_BRAVO_STATUS"),
        ("FALCON 456, runway B condition report", "RUNWAY_BRAVO_STATUS"),
        ("FALCON 789, runway Bravo hazard assessment", "RUNWAY_BRAVO_STATUS"),
        ("FALCON 321, requesting runway B safety status", "RUNWAY_BRAVO_STATUS"),
        
        # 사용 가능한 런웨이 문의
        ("FALCON 123, available runway status", "AVAILABLE_RUNWAY_INQUIRY"),
        ("FALCON 456, requesting active runway information", "AVAILABLE_RUNWAY_INQUIRY"),
        ("FALCON 789, which runway is available", "AVAILABLE_RUNWAY_INQUIRY"),
        ("FALCON 321, runway availability check", "AVAILABLE_RUNWAY_INQUIRY"),
    ]
    
    print("📊 전체 분류 정확도 테스트:")
    
    correct = 0
    total = len(test_data)
    category_stats = {}
    
    for text, expected in test_data:
        request_code, params = classifier.classify(text)
        is_correct = request_code == expected
        
        if is_correct:
            correct += 1
        
        # 카테고리별 통계
        if expected not in category_stats:
            category_stats[expected] = {"correct": 0, "total": 0}
        category_stats[expected]["total"] += 1
        if is_correct:
            category_stats[expected]["correct"] += 1
        
        print(f"  {'✅' if is_correct else '❌'} '{text[:50]}...'")
        print(f"     예상: {expected}, 결과: {request_code}")
    
    # 전체 정확도
    accuracy = correct / total * 100
    print(f"\n📈 전체 정확도: {correct}/{total} ({accuracy:.1f}%)")
    
    # 카테고리별 정확도
    print(f"\n📋 카테고리별 정확도:")
    for category, stats in category_stats.items():
        cat_accuracy = stats["correct"] / stats["total"] * 100
        print(f"  {category}: {stats['correct']}/{stats['total']} ({cat_accuracy:.1f}%)")
    
    return accuracy

def main():
    """메인 함수"""
    print("=== RequestClassifier 단위 테스트 ===\n")
    
    # 개별 카테고리 테스트
    test_bird_risk_inquiry()
    test_runway_alpha_status()
    test_runway_bravo_status()
    test_available_runway_inquiry()
    
    # 전체 정확도 테스트
    accuracy = test_classification_accuracy()
    
    print(f"\n{'='*60}")
    if accuracy >= 90:
        print(f"🎉 테스트 성공! 분류 정확도: {accuracy:.1f}%")
    elif accuracy >= 70:
        print(f"⚠️ 개선 필요. 분류 정확도: {accuracy:.1f}%")
    else:
        print(f"❌ 테스트 실패. 분류 정확도: {accuracy:.1f}%")

if __name__ == "__main__":
    main() 