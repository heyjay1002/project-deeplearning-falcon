#!/usr/bin/env python3
"""
Pilot GUI 테스트 실행 스크립트
"""

import sys
import os
import subprocess
from pathlib import Path

def run_test(test_path: str, description: str):
    """개별 테스트 실행"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"📁 {test_path}")
    print('='*60)
    
    try:
        result = subprocess.run([sys.executable, test_path], 
                              capture_output=False, 
                              text=True, 
                              cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ {description} - 성공")
            return True
        else:
            print(f"❌ {description} - 실패 (코드: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ {description} - 오류: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🚀 Pilot GUI 테스트 스위트 실행")
    
    # 테스트 목록 (경로, 설명)
    tests = [
        # 성능 테스트
        ("tests/performance/test_classifier.py", "요청 분류기 성능 테스트"),
        
        # STT 테스트 (기본)
        ("tests/stt/test_improved_recognition.py", "개선된 STT 인식률 테스트"),
        
        # 통합 테스트
        ("tests/integration/test_voice_controller.py", "음성 컨트롤러 통합 테스트"),
        
        # 메모리 테스트
        ("tests/memory/debug_memory_usage.py", "메모리 사용량 분석"),
    ]
    
    # 선택적 테스트 (시간이 오래 걸리는 것들)
    optional_tests = [
        ("tests/stt/test_english_medium.py", "Medium 모델 영어 STT 테스트"),
        ("tests/stt/test_medium_gpu.py", "Medium GPU STT 테스트"),
        ("tests/stt/test_large_gpu.py", "Large GPU STT 테스트 (메모리 집약적)"),
    ]
    
    print(f"\n📋 실행할 기본 테스트: {len(tests)}개")
    for i, (path, desc) in enumerate(tests, 1):
        print(f"  {i}. {desc}")
    
    print(f"\n📋 선택적 테스트: {len(optional_tests)}개")
    for i, (path, desc) in enumerate(optional_tests, 1):
        print(f"  {i}. {desc}")
    
    # 사용자 선택
    print(f"\n선택하세요:")
    print(f"1. 기본 테스트만 실행 (빠름)")
    print(f"2. 모든 테스트 실행 (느림)")
    print(f"3. 개별 테스트 선택")
    print(f"4. 종료")
    
    try:
        choice = input("\n선택 (1-4): ").strip()
        
        if choice == "1":
            # 기본 테스트만
            selected_tests = tests
        elif choice == "2":
            # 모든 테스트
            selected_tests = tests + optional_tests
        elif choice == "3":
            # 개별 선택
            print(f"\n실행할 테스트를 선택하세요 (쉼표로 구분, 예: 1,3,5):")
            all_tests = tests + optional_tests
            for i, (path, desc) in enumerate(all_tests, 1):
                print(f"  {i}. {desc}")
            
            indices = input("선택: ").strip().split(',')
            selected_tests = []
            for idx in indices:
                try:
                    i = int(idx.strip()) - 1
                    if 0 <= i < len(all_tests):
                        selected_tests.append(all_tests[i])
                except ValueError:
                    pass
        else:
            print("테스트 종료")
            return
        
        if not selected_tests:
            print("선택된 테스트가 없습니다.")
            return
        
        # 테스트 실행
        print(f"\n🏃 {len(selected_tests)}개 테스트 실행 시작...")
        
        passed = 0
        failed = 0
        
        for test_path, description in selected_tests:
            if Path(test_path).exists():
                if run_test(test_path, description):
                    passed += 1
                else:
                    failed += 1
            else:
                print(f"❌ 테스트 파일 없음: {test_path}")
                failed += 1
        
        # 결과 요약
        print(f"\n{'='*60}")
        print(f"🏆 테스트 결과 요약")
        print(f"{'='*60}")
        print(f"✅ 성공: {passed}개")
        print(f"❌ 실패: {failed}개")
        print(f"📊 성공률: {passed/(passed+failed)*100:.1f}%" if (passed+failed) > 0 else "N/A")
        
        if failed == 0:
            print(f"🎉 모든 테스트 통과!")
        else:
            print(f"⚠️ {failed}개 테스트 실패")
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 실행 오류: {e}")

if __name__ == "__main__":
    main() 