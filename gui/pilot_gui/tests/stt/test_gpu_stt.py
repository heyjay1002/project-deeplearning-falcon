#!/usr/bin/env python3
"""
GPU STT 테스트 스크립트
"""

import torch
from stt.whisper_engine import WhisperSTTEngine

def test_gpu_availability():
    """GPU 사용 가능성 테스트"""
    print("=== GPU 상태 확인 ===")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU 개수: {torch.cuda.device_count()}")
        print(f"현재 GPU: {torch.cuda.current_device()}")
        print(f"GPU 이름: {torch.cuda.get_device_name()}")
        
        # GPU 메모리 정보
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        allocated = torch.cuda.memory_allocated() / 1024**3
        cached = torch.cuda.memory_reserved() / 1024**3
        
        print(f"총 GPU 메모리: {total_memory:.1f}GB")
        print(f"할당된 메모리: {allocated:.2f}GB")
        print(f"캐시된 메모리: {cached:.2f}GB")
        print(f"사용 가능 메모리: {total_memory - allocated:.2f}GB")
    print()

def test_small_model():
    """작은 모델로 GPU 테스트"""
    print("=== 작은 모델 (base) GPU 테스트 ===")
    try:
        # base 모델로 테스트
        engine = WhisperSTTEngine(model_name="base", device="cuda")
        model_info = engine.get_model_info()
        
        print("모델 정보:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")
        
        if engine.is_model_loaded():
            print("✅ base 모델 GPU 로딩 성공!")
            
            # GPU 메모리 사용량 확인
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                print(f"모델 로딩 후 GPU 메모리 사용량: {allocated:.2f}GB")
        else:
            print("❌ 모델 로딩 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    print()

def test_medium_model():
    """medium 모델로 GPU 테스트"""
    print("=== medium 모델 GPU 테스트 ===")
    try:
        # 이전 모델 메모리 정리
        torch.cuda.empty_cache()
        
        # medium 모델로 테스트
        engine = WhisperSTTEngine(model_name="medium", device="cuda")
        model_info = engine.get_model_info()
        
        print("모델 정보:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")
        
        if engine.is_model_loaded():
            print("✅ medium 모델 GPU 로딩 성공!")
            
            # GPU 메모리 사용량 확인
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                print(f"모델 로딩 후 GPU 메모리 사용량: {allocated:.2f}GB")
        else:
            print("❌ 모델 로딩 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    print()

def main():
    """메인 함수"""
    test_gpu_availability()
    test_small_model()
    test_medium_model()
    
    print("=== 권장사항 ===")
    print("- RTX 2060 (6GB)에서는 medium 모델까지 안정적으로 실행 가능")
    print("- large-v2 모델은 메모리 부족으로 실행이 어려울 수 있음")
    print("- 성능 우선: medium 모델 (GPU)")
    print("- 안정성 우선: base 모델 (GPU) 또는 medium 모델 (CPU)")

if __name__ == "__main__":
    main() 