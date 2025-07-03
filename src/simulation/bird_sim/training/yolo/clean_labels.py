#!/usr/bin/env python3
"""
BirdRiskSim YOLO Label Cleaner
잘못된 라벨 좌표(0.0 미만 또는 1.0 초과)를 수정하는 스크립트
"""

import os
from pathlib import Path
from tqdm import tqdm

def clamp(value, min_val=0.0, max_val=1.0):
    """값을 지정된 범위 내로 제한"""
    return max(min_val, min(value, max_val))

def clean_labels(directory):
    """지정된 디렉토리의 모든 라벨 파일 수정"""
    
    label_files = list(Path(directory).glob("*.txt"))
    
    if not label_files:
        print(f"⚠️  '{directory}'에서 라벨 파일을 찾을 수 없습니다.")
        return 0, 0
        
    print(f"🧼 '{directory}' 디렉토리의 라벨 파일 {len(label_files)}개를 검사 및 수정합니다...")
    
    files_corrected = 0
    lines_corrected = 0
    
    for label_file in tqdm(label_files, desc=f"  - {Path(directory).name} 정리 중"):
        try:
            with open(label_file, 'r') as f:
                lines = f.readlines()

            new_lines = []
            is_corrected = False
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    new_lines.append(line)
                    continue

                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

                # 좌표 값 수정
                clamped_x = clamp(x_center)
                clamped_y = clamp(y_center)
                clamped_w = clamp(width)
                clamped_h = clamp(height)

                # 수정된 값이 있는지 확인
                if (clamped_x != x_center or clamped_y != y_center or
                    clamped_w != width or clamped_h != height):
                    is_corrected = True
                    lines_corrected += 1
                
                new_lines.append(f"{class_id} {clamped_x:.6f} {clamped_y:.6f} {clamped_w:.6f} {clamped_h:.6f}\n")

            if is_corrected:
                files_corrected += 1
                with open(label_file, 'w') as f:
                    f.writelines(new_lines)
                    
        except Exception as e:
            print(f"❌ '{label_file.name}' 파일 처리 중 오류 발생: {e}")

    return files_corrected, lines_corrected

def main():
    """메인 실행 함수"""
    print("🚀 데이터 라벨 클리닝 시작")
    print("=========================================")
    
    # training/yolo 경로
    training_root = Path(__file__).parent  # training/yolo
    
    # 라벨 디렉토리
    train_dir = training_root / "dataset/labels/train"
    val_dir = training_root / "dataset/labels/val"
    
    total_files_corrected = 0
    total_lines_corrected = 0
    
    # Train 데이터셋 정리
    train_files, train_lines = clean_labels(train_dir)
    total_files_corrected += train_files
    total_lines_corrected += train_lines
    
    print(f"  ✅ Train 완료: {train_files}개 파일, {train_lines}개 라인 수정")

    # Validation 데이터셋 정리
    val_files, val_lines = clean_labels(val_dir)
    total_files_corrected += val_files
    total_lines_corrected += val_lines
    print(f"  ✅ Val 완료: {val_files}개 파일, {val_lines}개 라인 수정")

    print("\n=========================================")
    if total_files_corrected > 0:
        print(f"🎉 총 {total_files_corrected}개 파일에서 {total_lines_corrected}개의 잘못된 라벨을 수정했습니다.")
    else:
        print("🎉 모든 라벨이 정상입니다. 수정할 필요가 없습니다.")
    print("이제 학습을 다시 시작할 수 있습니다.")

if __name__ == "__main__":
    main() 