#!/usr/bin/env python3
"""
BirdRiskSim YOLO Evaluation Script
학습된 YOLOv8s 모델의 상세한 성능 평가
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
from ultralytics import YOLO
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
import cv2
from collections import defaultdict

class ModelEvaluator:
    def __init__(self, model_path="weights/best_bird_detection.pt", dataset_yaml="dataset.yaml"):
        """
        평가 클래스 초기화
        
        Args:
            model_path: 학습된 모델 경로
            dataset_yaml: 데이터셋 설정 파일
        """
        self.model_path = model_path
        self.dataset_yaml = dataset_yaml
        self.model = None
        self.class_names = {0: 'Flock', 1: 'Airplane'}
        
        self.load_model()
    
    def load_model(self):
        """모델 로드"""
        if not Path(self.model_path).exists():
            print(f"❌ 모델 파일을 찾을 수 없습니다: {self.model_path}")
            return False
        
        try:
            self.model = YOLO(self.model_path)
            print(f"✅ 모델 로드 완료: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            return False
    
    def run_official_validation(self):
        """공식 YOLO validation 실행"""
        if self.model is None:
            print("❌ 모델이 로드되지 않았습니다.")
            return None
        
        print("🔍 공식 YOLO Validation 실행 중...")
        
        try:
            metrics = self.model.val(
                data=self.dataset_yaml, 
                save_json=True, 
                plots=True,
                verbose=True
            )
            
            print("\n📊 공식 평가 결과:")
            print(f"  mAP@0.5: {metrics.box.map50:.3f}")
            print(f"  mAP@0.5:0.95: {metrics.box.map:.3f}")
            print(f"  Precision: {metrics.box.mp:.3f}")
            print(f"  Recall: {metrics.box.mr:.3f}")
            print(f"  F1-Score: {metrics.box.f1:.3f}")
            
            # 클래스별 성능
            if hasattr(metrics.box, 'maps'):
                maps = metrics.box.maps
                print(f"\n📊 클래스별 mAP@0.5:")
                for i, map_score in enumerate(maps):
                    if i < len(self.class_names):
                        print(f"  {self.class_names[i]}: {map_score:.3f}")
            
            return metrics
            
        except Exception as e:
            print(f"❌ 평가 실행 실패: {e}")
            return None
    
    def analyze_predictions_on_dataset(self, confidence_threshold=0.25):
        """데이터셋에 대한 예측 분석"""
        print("🔍 데이터셋 예측 분석 중...")
        
        # 검증 데이터셋 경로
        val_images_dir = Path("dataset/images/val")
        val_labels_dir = Path("dataset/labels/val")
        
        if not val_images_dir.exists():
            print(f"❌ 검증 데이터를 찾을 수 없습니다: {val_images_dir}")
            return
        
        image_files = list(val_images_dir.glob("*.png"))
        
        predictions = []
        ground_truths = []
        detection_stats = defaultdict(int)
        
        print(f"📁 {len(image_files)}개 검증 이미지 분석 중...")
        
        for i, img_file in enumerate(image_files):
            if (i + 1) % 50 == 0:
                print(f"  처리 중: {i+1}/{len(image_files)}")
            
            # Ground Truth 로드
            label_file = val_labels_dir / f"{img_file.stem}.txt"
            gt_boxes = []
            
            if label_file.exists() and label_file.stat().st_size > 0:
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            gt_boxes.append(class_id)
            
            # 예측 수행
            results = self.model(str(img_file), conf=confidence_threshold, verbose=False)
            pred_boxes = []
            
            if results[0].boxes is not None:
                classes = results[0].boxes.cls.cpu().numpy().astype(int)
                confidences = results[0].boxes.conf.cpu().numpy()
                
                for cls, conf in zip(classes, confidences):
                    pred_boxes.append(cls)
                    detection_stats[f'{self.class_names[cls]}_detected'] += 1
            
            # 통계 수집
            ground_truths.extend(gt_boxes)
            predictions.extend(pred_boxes)
            
            # 이미지별 통계
            detection_stats['total_images'] += 1
            if gt_boxes:
                detection_stats['images_with_gt'] += 1
            if pred_boxes:
                detection_stats['images_with_pred'] += 1
        
        # 결과 분석
        self.analyze_detection_results(ground_truths, predictions, detection_stats)
    
    def analyze_detection_results(self, ground_truths, predictions, stats):
        """탐지 결과 상세 분석"""
        print("\n📊 상세 분석 결과:")
        print("=" * 50)
        
        # 기본 통계
        print(f"총 이미지: {stats['total_images']}")
        print(f"GT가 있는 이미지: {stats['images_with_gt']}")
        print(f"예측이 있는 이미지: {stats['images_with_pred']}")
        
        # 클래스별 탐지 수
        print(f"\n클래스별 탐지 수:")
        for cls_id, cls_name in self.class_names.items():
            key = f'{cls_name}_detected'
            count = stats.get(key, 0)
            print(f"  {cls_name}: {count}개")
        
        # Ground Truth 분포
        if ground_truths:
            gt_counts = np.bincount(ground_truths)
            print(f"\nGround Truth 분포:")
            for cls_id, count in enumerate(gt_counts):
                if cls_id in self.class_names:
                    print(f"  {self.class_names[cls_id]}: {count}개")
        
        # 예측 분포
        if predictions:
            pred_counts = np.bincount(predictions)
            print(f"\n예측 분포:")
            for cls_id, count in enumerate(pred_counts):
                if cls_id in self.class_names:
                    print(f"  {self.class_names[cls_id]}: {count}개")
        
        # 혼동 행렬 (클래스 수준에서만, 바운딩 박스 매칭은 복잡함)
        if ground_truths and predictions:
            self.plot_class_distribution(ground_truths, predictions)
    
    def plot_class_distribution(self, ground_truths, predictions):
        """클래스 분포 시각화"""
        # 클래스 분포 비교
        plt.figure(figsize=(15, 5))
        
        # Ground Truth 분포
        plt.subplot(1, 3, 1)
        gt_counts = np.bincount(ground_truths)
        classes = [self.class_names[i] for i in range(len(gt_counts)) if i in self.class_names]
        counts = [gt_counts[i] for i in range(len(gt_counts)) if i in self.class_names]
        
        plt.bar(classes, counts, color=['green', 'red'][:len(classes)])
        plt.title('Ground Truth 분포')
        plt.ylabel('개수')
        for i, v in enumerate(counts):
            plt.text(i, v + max(counts)*0.01, str(v), ha='center', va='bottom')
        
        # 예측 분포
        plt.subplot(1, 3, 2)
        pred_counts = np.bincount(predictions)
        pred_counts_list = [pred_counts[i] if i < len(pred_counts) else 0 
                           for i in range(len(self.class_names)) 
                           if i in self.class_names]
        
        plt.bar(classes, pred_counts_list, color=['lightgreen', 'lightcoral'][:len(classes)])
        plt.title('예측 분포')
        plt.ylabel('개수')
        for i, v in enumerate(pred_counts_list):
            plt.text(i, v + max(pred_counts_list)*0.01, str(v), ha='center', va='bottom')
        
        # 비교
        plt.subplot(1, 3, 3)
        x = np.arange(len(classes))
        width = 0.35
        
        plt.bar(x - width/2, counts, width, label='Ground Truth', color=['green', 'red'][:len(classes)], alpha=0.7)
        plt.bar(x + width/2, pred_counts_list, width, label='Predictions', color=['lightgreen', 'lightcoral'][:len(classes)], alpha=0.7)
        
        plt.title('GT vs 예측 비교')
        plt.ylabel('개수')
        plt.xticks(x, classes)
        plt.legend()
        
        plt.tight_layout()
        
        # 결과 저장
        output_dir = Path("training/results/evaluation")
        output_dir.mkdir(exist_ok=True)
        
        # 클래스 분포 그래프 저장
        plt.savefig(output_dir / 'class_distribution.png', dpi=300, bbox_inches='tight')
        print(f"✅ 클래스 분포 그래프 저장: {output_dir}/class_distribution.png")
    
    def confidence_analysis(self, confidence_thresholds=[0.1, 0.25, 0.5, 0.75, 0.9]):
        """신뢰도 임계값별 성능 분석"""
        print("🔍 신뢰도 임계값별 성능 분석...")
        
        val_images_dir = Path("dataset/images/val")
        image_files = list(val_images_dir.glob("*.png"))[:100]  # 샘플링
        
        results = []
        
        for conf_thresh in confidence_thresholds:
            total_detections = 0
            class_counts = {0: 0, 1: 0}
            
            for img_file in image_files:
                preds = self.model(str(img_file), conf=conf_thresh, verbose=False)
                
                if preds[0].boxes is not None:
                    classes = preds[0].boxes.cls.cpu().numpy().astype(int)
                    total_detections += len(classes)
                    
                    for cls in classes:
                        class_counts[cls] += 1
            
            results.append({
                'confidence': conf_thresh,
                'total_detections': total_detections,
                'flock_detections': class_counts[0],
                'airplane_detections': class_counts[1]
            })
        
        # 결과 시각화
        df = pd.DataFrame(results)
        
        plt.figure(figsize=(12, 4))
        
        plt.subplot(1, 2, 1)
        plt.plot(df['confidence'], df['total_detections'], 'o-', label='Total')
        plt.plot(df['confidence'], df['flock_detections'], 's-', label='Flock')
        plt.plot(df['confidence'], df['airplane_detections'], '^-', label='Airplane')
        plt.xlabel('Confidence Threshold')
        plt.ylabel('Detection Count')
        plt.title('신뢰도별 탐지 수')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.subplot(1, 2, 2)
        flock_ratio = df['flock_detections'] / (df['flock_detections'] + df['airplane_detections'] + 1e-6)
        airplane_ratio = df['airplane_detections'] / (df['flock_detections'] + df['airplane_detections'] + 1e-6)
        
        plt.plot(df['confidence'], flock_ratio, 's-', label='Flock %', color='green')
        plt.plot(df['confidence'], airplane_ratio, '^-', label='Airplane %', color='red')
        plt.xlabel('Confidence Threshold')
        plt.ylabel('Class Ratio')
        plt.title('신뢰도별 클래스 비율')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 신뢰도 분석 그래프 저장
        plt.savefig(output_dir / 'confidence_analysis.png', dpi=300, bbox_inches='tight')
        print(f"✅ 신뢰도 분석 저장: {output_dir}/confidence_analysis.png")
        
        # 결과 표 출력
        print(f"\n📊 신뢰도별 탐지 결과:")
        print(df.to_string(index=False))

def main():
    parser = argparse.ArgumentParser(description='BirdRiskSim YOLO Evaluation')
    parser.add_argument('--model', type=str, default='weights/best_bird_detection.pt',
                       help='Model path')
    parser.add_argument('--data', type=str, default='dataset.yaml',
                       help='Dataset YAML path')
    parser.add_argument('--conf', type=float, default=0.25,
                       help='Confidence threshold for analysis')
    parser.add_argument('--skip-official', action='store_true',
                       help='Skip official YOLO validation')
    
    args = parser.parse_args()
    
    print("🚀 BirdRiskSim YOLO 모델 평가 시작")
    print("=" * 60)
    
    # 평가 객체 생성
    evaluator = ModelEvaluator(args.model, args.data)
    
    if evaluator.model is None:
        return
    
    # 결과 폴더 생성
    output_dir = Path("training/results/evaluation")
    output_dir.mkdir(exist_ok=True)
    
    # 1. 공식 검증
    if not args.skip_official:
        print("\n1️⃣ 공식 YOLO Validation...")
        metrics = evaluator.run_official_validation()
    
    # 2. 예측 분석
    print("\n2️⃣ 데이터셋 예측 분석...")
    evaluator.analyze_predictions_on_dataset(args.conf)
    
    # 3. 신뢰도 분석
    print("\n3️⃣ 신뢰도 임계값 분석...")
    evaluator.confidence_analysis()
    
    print(f"\n🎉 평가 완료!")
    print(f"📁 결과 폴더: {output_dir}/")
    print("=" * 60)

if __name__ == "__main__":
    main() 