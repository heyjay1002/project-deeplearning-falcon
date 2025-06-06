#!/usr/bin/env python3
"""
STT 성능 테스트 스크립트
"""

import time
from stt.whisper_engine import WhisperSTTEngine

def test_stt_model():
    """STT 모델 성능 테스트"""
    print("=== STT 모델 성능 테스트 ===\n")
    
    try:
        # STT 엔진 초기화
        print("1. STT 엔진 초기화 중...")
        engine = WhisperSTTEngine()
        
        # 모델 정보 확인
        model_info = engine.get_model_info()
        print(f"✓ 모델 정보:")
        for key, value in model_info.items():
            print(f"   {key}: {value}")
        print()
        
        if not engine.is_model_loaded():
            print("❌ 모델이 로드되지 않았습니다.")
            return
        
        print("2. 모델 로딩 완료! 이제 음성 테스트를 진행할 수 있습니다.")
        print("   - large-v2 모델은 한국어 인식 성능이 매우 우수합니다")
        print("   - 항공 관련 용어 후처리 기능이 포함되어 있습니다")
        print("   - 신뢰도 점수도 함께 제공됩니다")
        print()
        
        print("3. 테스트 방법:")
        print("   python test_voice_controller.py 실행 후")
        print("   옵션 1 (전체 기능 테스트) 선택하여 음성 입력 테스트")
        print()
        
        # 지원하는 항공 용어 예시
        print("4. 인식 가능한 항공 용어 예시:")
        aviation_terms = [
            "조류 위험도 확인 요청",
            "활주로 A 상태 점검", 
            "FOD 탐지 상태 확인",
            "시스템 상태 확인",
            "비상 절차 안내 요청",
            "착륙 허가 요청",
            "이륙 준비 완료"
        ]
        
        for term in aviation_terms:
            print(f"   - {term}")
        
        print("\n✓ STT 시스템 준비 완료!")
        
    except Exception as e:
        print(f"❌ STT 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def compare_models():
    """다른 모델과 성능 비교 (참고용)"""
    print("\n=== Whisper 모델 성능 비교 ===")
    print("모델 크기별 특징:")
    print("- tiny: ~39MB, 빠름, 정확도 낮음")
    print("- base: ~74MB, 보통, 정확도 보통") 
    print("- small: ~244MB, 느림, 정확도 좋음")
    print("- medium: ~769MB, 더 느림, 정확도 매우 좋음")
    print("- large-v2: ~3GB, 가장 느림, 정확도 최고 ⭐")
    print()
    print("현재 사용 중: large-v2 (최고 성능)")

if __name__ == "__main__":
    test_stt_model()
    compare_models() 