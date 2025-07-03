#!/usr/bin/env python3
"""
BirdRiskSim YOLO Training Setup
YOLO 학습을 위한 데이터 준비 및 환경 구축 스크립트
"""

import os
import shutil
import random
from pathlib import Path
import yaml
from collections import defaultdict

def get_project_root():
    """프로젝트 루트 디렉토리 경로 반환"""
    current_dir = Path(__file__).parent
    return current_dir.parent.parent  # training/yolo -> BirdRiskSim

def setup_yolo_structure():
    """YOLO 학습을 위한 디렉토리 구조 생성"""
    
    # training/yolo 경로
    training_root = Path(__file__).parent  # training/yolo
    
    # 기본 디렉토리 구조
    dirs = [
        "dataset/images/train",
        "dataset/images/val",
        "dataset/labels/train",
        "dataset/labels/val",
        "runs",
        "weights"
    ]
    
    for dir_path in dirs:
        os.makedirs(training_root / dir_path, exist_ok=True)
        print(f"✅ Created: training/yolo/{dir_path}")

def collect_data_info():
    """데이터 정보 수집"""
    project_root = get_project_root()
    source_dir = project_root / "data" / "yolo_capture"  # BirdRiskSim/data/yolo_capture
    
    if not source_dir.exists():
        raise FileNotFoundError(f"데이터 디렉토리를 찾을 수 없습니다: {source_dir}")
    
    all_files = []
    stats = defaultdict(int)
    
    for camera_dir in source_dir.iterdir():
        if camera_dir.is_dir():
            print(f"📁 Processing {camera_dir.name}...")
            
            for img_file in camera_dir.glob("*.png"):
                label_file = img_file.with_suffix('.txt')
                
                if label_file.exists():
                    all_files.append({
                        'image': img_file,
                        'label': label_file,
                        'camera': camera_dir.name
                    })
                    stats[camera_dir.name] += 1
                else:
                    print(f"⚠️  Missing label: {img_file}")
    
    print(f"\n📊 데이터 통계:")
    for camera, count in stats.items():
        print(f"  {camera}: {count}개 파일")
    print(f"  총 {len(all_files)}개 파일")
    
    return all_files

def split_dataset(all_files, train_ratio=0.8, val_ratio=0.2):
    """데이터셋을 train/val로 분할"""
    
    # 셔플
    random.shuffle(all_files)
    
    total = len(all_files)
    train_size = int(total * train_ratio)
    
    train_files = all_files[:train_size]
    val_files = all_files[train_size:]
    
    print(f"\n📊 데이터 분할:")
    print(f"  Train: {len(train_files)}개 ({len(train_files)/total*100:.1f}%)")
    print(f"  Val: {len(val_files)}개 ({len(val_files)/total*100:.1f}%)")
    
    return train_files, val_files

def copy_files(files, split_name):
    """파일들을 해당 디렉토리로 복사"""
    
    print(f"\n📁 {split_name} 파일 복사 중...")
    
    training_root = Path(__file__).parent  # training/yolo
    
    for i, file_info in enumerate(files):
        # 새로운 파일명 (카메라 정보 포함)
        camera = file_info['camera']
        orig_name = file_info['image'].stem
        new_name = f"{camera}_{orig_name}"
        
        # 이미지 복사
        dst_img = training_root / f"dataset/images/{split_name}/{new_name}.png"
        shutil.copy2(file_info['image'], dst_img)
        
        # 라벨 복사
        dst_label = training_root / f"dataset/labels/{split_name}/{new_name}.txt"
        shutil.copy2(file_info['label'], dst_label)
        
        if (i + 1) % 500 == 0:
            print(f"  복사 완료: {i + 1}/{len(files)}")
    
    print(f"✅ {split_name} 복사 완료: {len(files)}개 파일")

def create_yaml_config():
    """YOLO 설정 파일 생성"""
    
    training_root = Path(__file__).parent  # training/yolo
    
    config = {
        'path': str(training_root / 'dataset'),
        'train': 'images/train',
        'val': 'images/val',
        'test': None,  # optional
        
        'names': {
            0: 'Flock',    # 새떼
            1: 'Airplane'  # 비행기
        },
        
        'nc': 2  # number of classes
    }
    
    yaml_path = training_root / 'dataset/dataset.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print("✅ dataset.yaml 생성 완료")
    
    return config

def analyze_labels():
    """라벨 데이터 분석"""
    training_root = Path(__file__).parent  # training/yolo
    train_labels = training_root / "dataset/labels/train"
    val_labels = training_root / "dataset/labels/val"
    
    class_counts = defaultdict(int)
    total_objects = 0
    
    for split_dir in [train_labels, val_labels]:
        for label_file in split_dir.glob("*.txt"):
            if label_file.stat().st_size > 0:  # 빈 파일이 아닌 경우
                with open(label_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            class_id = int(line.split()[0])
                            class_counts[class_id] += 1
                            total_objects += 1
    
    print(f"\n📊 라벨 분석:")
    print(f"  총 객체 수: {total_objects}")
    for class_id, count in class_counts.items():
        class_name = "Flock" if class_id == 0 else "Airplane"
        print(f"  {class_name} (클래스 {class_id}): {count}개 ({count/total_objects*100:.1f}%)")

def main():
    """메인 실행 함수"""
    print("🚀 BirdRiskSim YOLO 학습 환경 구축 시작")
    print("=" * 50)
    
    # 1. 디렉토리 구조 생성
    print("\n1️⃣ 디렉토리 구조 생성...")
    setup_yolo_structure()
    
    # 2. 데이터 정보 수집
    print("\n2️⃣ 데이터 정보 수집...")
    all_files = collect_data_info()
    
    if not all_files:
        print("❌ 데이터를 찾을 수 없습니다!")
        return
    
    # 3. 데이터 분할
    print("\n3️⃣ 데이터 분할...")
    train_files, val_files = split_dataset(all_files)
    
    # 4. 파일 복사
    print("\n4️⃣ 파일 복사...")
    copy_files(train_files, "train")
    copy_files(val_files, "val")
    
    # 5. YAML 설정 파일 생성
    print("\n5️⃣ 설정 파일 생성...")
    create_yaml_config()
    
    # 6. 라벨 분석
    print("\n6️⃣ 라벨 분석...")
    analyze_labels()
    
    print("\n🎉 YOLO 학습 환경 구축 완료!")
    print("=" * 50)
    print("다음 단계:")
    print("  1. train.py 실행하여 학습 시작")
    print("  2. tensorboard --logdir runs 로 학습 모니터링")

if __name__ == "__main__":
    # 시드 설정
    random.seed(42)
    main() 