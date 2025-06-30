#!/usr/bin/env python3
"""
BirdRiskSim YOLO Inference Script
학습된 YOLOv8s 모델을 사용한 새떼-비행기 탐지 추론
"""

import os
import cv2
import numpy as np
from pathlib import Path
import argparse
from ultralytics import YOLO
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime

class BirdDetectionInference:
    def __init__(self, model_path="weights/best_bird_detection.pt"):
        """
        추론 클래스 초기화
        
        Args:
            model_path: 학습된 모델 경로
        """
        self.model_path = model_path
        self.model = None
        self.class_names = {0: 'Flock', 1: 'Airplane'}
        self.colors = {0: (0, 255, 0), 1: (255, 0, 0)}  # Flock: 초록, Airplane: 빨강
        
        self.load_model()
    
    def load_model(self):
        """모델 로드"""
        if not Path(self.model_path).exists():
            print(f"❌ 모델 파일을 찾을 수 없습니다: {self.model_path}")
            print("   먼저 train.py를 실행하여 모델을 학습하세요.")
            return False
        
        try:
            self.model = YOLO(self.model_path)
            print(f"✅ 모델 로드 완료: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            return False
    
    def predict_image(self, image_path, conf_threshold=0.25, save_result=True):
        """
        단일 이미지 추론
        
        Args:
            image_path: 이미지 경로
            conf_threshold: 신뢰도 임계값
            save_result: 결과 저장 여부
        """
        if self.model is None:
            print("❌ 모델이 로드되지 않았습니다.")
            return None
        
        # 이미지 로드
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"❌ 이미지를 로드할 수 없습니다: {image_path}")
            return None
        
        # 추론 수행
        results = self.model(image, conf=conf_threshold, verbose=False)
        result = results[0]
        
        # 결과 분석
        detections = []
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)
            
            for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                x1, y1, x2, y2 = box
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf,
                    'class': cls,
                    'class_name': self.class_names[cls]
                })
        
        # 결과 시각화 및 저장
        if save_result:
            self.visualize_and_save(image, detections, image_path)
        
        return detections
    
    def visualize_and_save(self, image, detections, original_path):
        """결과 시각화 및 저장"""
        # OpenCV BGR을 RGB로 변환
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # matplotlib 설정
        plt.figure(figsize=(12, 8))
        plt.imshow(image_rgb)
        plt.axis('off')
        
        # 탐지 결과 그리기
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            conf = detection['confidence']
            cls = detection['class']
            class_name = detection['class_name']
            
            # 바운딩 박스
            width, height = x2 - x1, y2 - y1
            rect = patches.Rectangle(
                (x1, y1), width, height,
                linewidth=2, edgecolor=np.array(self.colors[cls])/255,
                facecolor='none'
            )
            plt.gca().add_patch(rect)
            
            # 라벨
            label = f'{class_name}: {conf:.2f}'
            plt.text(x1, y1-5, label, 
                    bbox=dict(boxstyle="round,pad=0.3", 
                             facecolor=np.array(self.colors[cls])/255, 
                             alpha=0.7),
                    fontsize=10, color='white', weight='bold')
        
        # 제목
        plt.title(f'탐지 결과: {len(detections)}개 객체 발견', fontsize=14, weight='bold')
        
        # 저장
        output_dir = Path("training/yolo/results/detections")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = Path(original_path).stem
        output_path = output_dir / f"{original_name}_detected_{timestamp}.png"
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 결과 저장됨: {output_path}")
    
    def predict_folder(self, folder_path, conf_threshold=0.25, max_images=None):
        """
        폴더 내 모든 이미지 추론
        
        Args:
            folder_path: 이미지 폴더 경로
            conf_threshold: 신뢰도 임계값
            max_images: 최대 처리할 이미지 수
        """
        folder = Path(folder_path)
        if not folder.exists():
            print(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
            return
        
        # 이미지 파일 찾기
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(folder.glob(f"*{ext}"))
            image_files.extend(folder.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"❌ 이미지 파일을 찾을 수 없습니다: {folder_path}")
            return
        
        # 최대 이미지 수 제한
        if max_images:
            image_files = image_files[:max_images]
        
        print(f"📁 {len(image_files)}개 이미지 처리 시작...")
        
        # 통계
        total_detections = 0
        class_counts = {0: 0, 1: 0}
        
        for i, image_file in enumerate(image_files):
            print(f"🔍 처리 중: {image_file.name} ({i+1}/{len(image_files)})")
            
            detections = self.predict_image(image_file, conf_threshold)
            if detections:
                total_detections += len(detections)
                for det in detections:
                    class_counts[det['class']] += 1
        
        # 결과 요약
        print(f"\n📊 처리 완료!")
        print(f"  총 이미지: {len(image_files)}개")
        print(f"  총 탐지: {total_detections}개")
        print(f"  Flock 탐지: {class_counts[0]}개")
        print(f"  Airplane 탐지: {class_counts[1]}개")
        print(f"  결과 폴더: inference_results/")

def main():
    parser = argparse.ArgumentParser(description='BirdRiskSim YOLO Inference')
    parser.add_argument('--model', type=str, default='weights/best_bird_detection.pt',
                       help='Model path')
    parser.add_argument('--source', type=str, required=True,
                       help='Image file or folder path')
    parser.add_argument('--conf', type=float, default=0.25,
                       help='Confidence threshold')
    parser.add_argument('--max-images', type=int, default=None,
                       help='Maximum number of images to process')
    
    args = parser.parse_args()
    
    print("🚀 BirdRiskSim YOLO 추론 시작")
    print("=" * 50)
    
    # 추론 객체 생성
    detector = BirdDetectionInference(args.model)
    
    if detector.model is None:
        return
    
    source_path = Path(args.source)
    
    if source_path.is_file():
        # 단일 파일 처리
        print(f"📸 단일 이미지 처리: {source_path}")
        detections = detector.predict_image(source_path, args.conf)
        
        if detections:
            print(f"✅ {len(detections)}개 객체 탐지됨:")
            for i, det in enumerate(detections):
                print(f"  {i+1}. {det['class_name']}: {det['confidence']:.3f}")
        else:
            print("❌ 탐지된 객체가 없습니다.")
    
    elif source_path.is_dir():
        # 폴더 처리
        print(f"📁 폴더 처리: {source_path}")
        detector.predict_folder(source_path, args.conf, args.max_images)
    
    else:
        print(f"❌ 경로를 찾을 수 없습니다: {args.source}")

if __name__ == "__main__":
    main() 