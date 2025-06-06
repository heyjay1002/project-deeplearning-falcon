#!/usr/bin/env python3
"""
개선된 쿼리 분류기 테스트
"""

from query_parser.request_classifier import RequestClassifier

def test_improved_classifier():
    classifier = RequestClassifier()
    test_queries = [
        'KAL123, 조류 위험도 확인 요청',
        'AAR456, 활주로 A 상태 점검',
        'UAL789, FOD 탐지 상태는?',
        'DLH012, 시스템 상태 확인',
        'SIA345, 비상 절차 안내 요청',
        'JAL456, 활주로 B 폐쇄 요청',
        'KLM789, 착륙 허가 요청',
        'LH012, 이륙 준비 완료'
    ]
    
    print('=== 개선된 쿼리 분류 테스트 ===\n')
    
    for query in test_queries:
        request_code, params = classifier.classify(query)
        print(f'입력: {query}')
        print(f'결과: {request_code} (점수: {params.get("confidence_score", 0)})')
        print(f'매칭 키워드: {params.get("matched_keywords", [])}')
        print()

if __name__ == "__main__":
    test_improved_classifier() 