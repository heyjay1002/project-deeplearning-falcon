#!/usr/bin/env python3
"""
Whisper 모델 메모리 사용량 디버깅
"""

import torch
import whisper
import gc
import os

def debug_memory_step(step_name):
    """메모리 사용량 출력"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        cached = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"{step_name}: 할당={allocated:.2f}GB, 캐시={cached:.2f}GB, 총사용={allocated+cached:.2f}GB")
        return allocated + cached
    return 0

def debug_whisper_loading():
    """Whisper 모델 로딩 과정 디버깅"""
    print("=== Whisper 모델 로딩 메모리 디버깅 ===")
    
    if not torch.cuda.is_available():
        print("❌ CUDA 사용 불가")
        return
    
    # 초기 상태
    torch.cuda.empty_cache()
    gc.collect()
    debug_memory_step("1. 초기 상태")
    
    # PyTorch 설정
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:256'
    torch.cuda.set_per_process_memory_fraction(0.98)
    debug_memory_step("2. PyTorch 설정 후")
    
    # 각 모델별 메모리 사용량 확인
    models_to_test = ["tiny", "base", "small", "medium"]
    
    for model_name in models_to_test:
        print(f"\n--- {model_name} 모델 테스트 ---")
        
        # 메모리 정리
        torch.cuda.empty_cache()
        gc.collect()
        before_memory = debug_memory_step(f"{model_name} 로딩 전")
        
        try:
            # 모델 로딩
            print(f"{model_name} 모델 로딩 중...")
            model = whisper.load_model(model_name, device="cuda")
            after_memory = debug_memory_step(f"{model_name} 로딩 후")
            
            # 실제 사용량 계산
            used_memory = after_memory - before_memory
            print(f"✅ {model_name} 모델 실제 사용량: {used_memory:.2f}GB")
            
            # 모델 정리
            del model
            torch.cuda.empty_cache()
            gc.collect()
            debug_memory_step(f"{model_name} 정리 후")
            
        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                print(f"❌ {model_name} 모델 메모리 부족: {e}")
                break
            else:
                print(f"❌ {model_name} 모델 오류: {e}")
    
    # Large 모델 시도 (실패 예상)
    print(f"\n--- large-v2 모델 테스트 ---")
    torch.cuda.empty_cache()
    gc.collect()
    before_memory = debug_memory_step("large-v2 로딩 전")
    
    try:
        print("large-v2 모델 로딩 시도...")
        model = whisper.load_model("large-v2", device="cuda")
        after_memory = debug_memory_step("large-v2 로딩 후")
        used_memory = after_memory - before_memory
        print(f"🏆 large-v2 모델 실제 사용량: {used_memory:.2f}GB")
        del model
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            print(f"❌ large-v2 모델 메모리 부족")
            # 오류 메시지에서 실제 필요 메모리 추출
            import re
            match = re.search(r'Tried to allocate (\d+\.\d+) (\w+)', str(e))
            if match:
                size = float(match.group(1))
                unit = match.group(2)
                if unit == "MiB":
                    size_gb = size / 1024
                elif unit == "GiB":
                    size_gb = size
                print(f"추가 필요 메모리: {size_gb:.2f}GB")
                print(f"예상 총 필요량: {before_memory + size_gb:.2f}GB")
        else:
            print(f"❌ large-v2 모델 기타 오류: {e}")

def check_whisper_model_sizes():
    """Whisper 모델 공식 크기 확인"""
    print("\n=== Whisper 모델 공식 크기 ===")
    
    # Whisper 모델 정보 (공식)
    model_info = {
        "tiny": "39 MB",
        "base": "74 MB", 
        "small": "244 MB",
        "medium": "769 MB",
        "large": "1550 MB",
        "large-v2": "1550 MB",
        "large-v3": "1550 MB"
    }
    
    for model, size in model_info.items():
        print(f"{model:10}: {size}")
    
    print("\n❓ 그런데 왜 GPU에서는 더 많은 메모리를 사용할까?")
    print("1. 모델 가중치 로딩")
    print("2. GPU 메모리 정렬 및 패딩")
    print("3. 중간 계산 버퍼")
    print("4. PyTorch 오버헤드")

if __name__ == "__main__":
    check_whisper_model_sizes()
    debug_whisper_loading() 