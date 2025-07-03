#!/usr/bin/env python3
"""
BirdRiskSim YOLO Training Script
YOLOv8을 사용한 새떼-비행기 탐지 모델 학습
"""

import os
import yaml
from pathlib import Path
import torch
from ultralytics import YOLO
import argparse
from datetime import datetime

def check_environment():
    """학습 환경 확인"""
    print("🔍 학습 환경 확인...")
    
    # CUDA 확인
    cuda_available = torch.cuda.is_available()
    print(f"  CUDA 사용 가능: {cuda_available}")
    
    if cuda_available:
        print(f"  GPU 개수: {torch.cuda.device_count()}")
        print(f"  현재 GPU: {torch.cuda.get_device_name()}")
        print(f"  GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    
    # training/yolo 경로
    training_root = Path(__file__).parent  # training/yolo
    
    # 데이터셋 확인
    yaml_path = training_root / "dataset/dataset.yaml"
    if not yaml_path.exists():
        print("❌ dataset.yaml 파일이 없습니다!")
        print("   먼저 setup_training.py를 실행하세요.")
        return False
    
    # 이미지 폴더 확인
    train_images = training_root / "dataset/images/train"
    val_images = training_root / "dataset/images/val"
    
    if not train_images.exists() or not val_images.exists():
        print("❌ 데이터셋 폴더가 없습니다!")
        print("   먼저 setup_training.py를 실행하세요.")
        return False
    
    train_count = len(list(train_images.glob("*.png")))
    val_count = len(list(val_images.glob("*.png")))
    
    print(f"  훈련 이미지: {train_count}개")
    print(f"  검증 이미지: {val_count}개")
    
    if train_count == 0:
        print("❌ 훈련 이미지가 없습니다!")
        return False
    
    return True

def get_best_model_size(train_count):
    """데이터 수에 따른 최적 모델 크기 선택 - 기본 YOLOv8s 사용"""
    # 사용자 요청에 따라 YOLOv8s를 기본으로 사용
    return "yolov8s.pt"  # Small - 균형잡힌 성능, 사용자 지정

def create_training_config():
    """학습 설정 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    config = {
        'project': 'runs/train',  # 이후에 절대 경로로 변경됨
        'name': f'bird_detection_{timestamp}',
        'data': 'dataset.yaml',
        'epochs': 150,  # 에폭 수 증가
        'batch': 8,
        'imgsz': 640,
        'device': 'auto',
        'workers': 8,
        'patience': 30,  # Early stopping 인내심 증가
        'save_period': 10,
        'cache': True,
        'amp': True,
        'val': True,
        'plots': True,
        'verbose': True,
        
        # 하이퍼파라미터 최적화
        'lr0': 0.01,
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 5,  # 워밍업 에폭 증가
        'warmup_momentum': 0.8,
        'box': 7.5,
        'cls': 0.5,
        'dfl': 1.5,
        
        # NMS 및 신뢰도 임계값 조정
        'conf': 0.4,  # 신뢰도 임계값 상향
        'iou': 0.5,   # NMS IOU 임계값
        
        # 데이터 증강 강화
        'hsv_h': 0.015,  # HSV 색상 증강
        'hsv_s': 0.7,
        'hsv_v': 0.4,
        'degrees': 10.0,  # 회전 증강
        'translate': 0.2,  # 이동 증강
        'scale': 0.5,     # 크기 증강
        'shear': 2.0,     # 기울기 증강
        'perspective': 0.0,  # 원근 증강
        'flipud': 0.5,    # 상하 반전
        'fliplr': 0.5,    # 좌우 반전
        'mosaic': 1.0,    # 모자이크 증강
        'mixup': 0.5,     # 믹스업 증강
        'copy_paste': 0.5,  # 복사-붙여넣기 증강
    }
    
    return config

def main():
    parser = argparse.ArgumentParser(description='BirdRiskSim YOLO Training')
    parser.add_argument('--model', type=str, default='yolov8s', 
                       help='Model size (yolov8n/s/m/l/x or auto)')
    parser.add_argument('--epochs', type=int, default=100, 
                       help='Number of epochs')
    parser.add_argument('--batch', type=int, default=8, 
                       help='Batch size (8 for default)')
    parser.add_argument('--imgsz', type=int, default=640, 
                       help='Image size')
    parser.add_argument('--resume', type=str, default=None, 
                       help='Resume from checkpoint')
    parser.add_argument('--pretrained', action='store_true', 
                       help='Use pretrained weights')
    
    args = parser.parse_args()
    
    print("🚀 BirdRiskSim YOLO 학습 시작")
    print("=" * 60)
    
    # 1. 환경 확인
    if not check_environment():
        return
    
    # 2. 모델 선택
    if args.model == 'auto':
        training_root = Path(__file__).parent  # training/yolo
        train_count = len(list((training_root / "dataset/images/train").glob("*.png")))
        model_name = get_best_model_size(train_count)
        print(f"  자동 선택된 모델: {model_name}")
    else:
        model_name = args.model if args.model.endswith('.pt') else f'{args.model}.pt'
    
    print(f"📊 사용할 모델: {model_name}")
    
    # 3. 모델 로드
    try:
        if args.resume:
            print(f"🔄 체크포인트에서 재시작: {args.resume}")
            model = YOLO(args.resume)
        else:
            model = YOLO(model_name)
            print(f"✅ 모델 로드 완료: {model_name}")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return
    
    # 4. 학습 설정
    config = create_training_config()
    config['epochs'] = args.epochs
    config['batch'] = args.batch
    config['imgsz'] = args.imgsz
    
    # dataset.yaml 및 project 절대 경로 설정
    training_root = Path(__file__).parent  # training/yolo
    config['data'] = str(training_root / "dataset/dataset.yaml")
    config['project'] = str(training_root / "runs/train")
    
    print(f"\n📋 학습 설정:")
    print(f"  Epochs: {config['epochs']}")
    print(f"  Batch Size: {config['batch']}")
    print(f"  Image Size: {config['imgsz']}")
    print(f"  Device: {config['device']}")
    print(f"  Mixed Precision: {config['amp']}")
    print(f"  Cache: {config['cache']}")
    
    # 5. 학습 시작
    print(f"\n🎯 학습 시작...")
    print("=" * 60)
    
    try:
        results = model.train(
            data=config['data'],
            epochs=config['epochs'],
            batch=config['batch'],
            imgsz=config['imgsz'],
            device=config['device'],
            workers=config['workers'],
            patience=config['patience'],
            save_period=config['save_period'],
            cache=config['cache'],
            amp=config['amp'],
            project=config['project'],
            name=config['name'],
            plots=config['plots'],
            verbose=config['verbose'],
            
            # 하이퍼파라미터
            lr0=config['lr0'],
            momentum=config['momentum'],
            weight_decay=config['weight_decay'],
            warmup_epochs=config['warmup_epochs'],
            warmup_momentum=config['warmup_momentum'],
            box=config['box'],
            cls=config['cls'],
            dfl=config['dfl'],
        )
        
        print("\n🎉 학습 완료!")
        print("=" * 60)
        print(f"📁 결과 폴더: {config['project']}/{config['name']}")
        print(f"🏆 Best 모델: {config['project']}/{config['name']}/weights/best.pt")
        print(f"📊 Last 모델: {config['project']}/{config['name']}/weights/last.pt")
        
        # 6. 최종 평가
        print("\n📊 최종 모델 평가...")
        metrics = model.val()
        
        print(f"  mAP@0.5: {metrics.box.map50:.3f}")
        print(f"  mAP@0.5:0.95: {metrics.box.map:.3f}")
        print(f"  Precision: {metrics.box.mp:.3f}")
        print(f"  Recall: {metrics.box.mr:.3f}")
        
        # 7. 모델 내보내기
        best_model_path = f"{config['project']}/{config['name']}/weights/best.pt"
        training_root = Path(__file__).parent  # training/yolo
        export_path = training_root / "weights/best_bird_detection.pt"
        
        if Path(best_model_path).exists():
            import shutil
            shutil.copy2(best_model_path, export_path)
            print(f"✅ 최적 모델 저장: {export_path}")
        
        print("\n🚀 학습 완료! 다음 단계:")
        print("  1. tensorboard --logdir training/yolo/runs/train 으로 결과 확인")
        print("  2. inference.py 로 추론 테스트")
        print("  3. evaluate.py 로 상세 평가")
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 학습이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 