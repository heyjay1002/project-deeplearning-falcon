#!/usr/bin/env python3
"""
BirdRiskSim YOLO Inference Script
YOLO model inference for bird flock and airplane detection
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
        Initialize inference class
        
        Args:
            model_path: Path to trained model
        """
        self.model_path = model_path
        self.model = None
        self.class_names = {0: 'Flock', 1: 'Airplane'}
        self.colors = {0: (0, 255, 0), 1: (255, 0, 0)}  # Flock: Green, Airplane: Red
        
        self.load_model()
    
    def load_model(self):
        """Load YOLO model"""
        if not Path(self.model_path).exists():
            print(f"❌ Model file not found: {self.model_path}")
            print("   Please run train.py first to train the model.")
            return False
        
        try:
            self.model = YOLO(self.model_path)
            print(f"✅ Model loaded successfully: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False
    
    def predict_image(self, image_path, conf_threshold=0.25, save_result=True):
        """
        Inference on single image
        
        Args:
            image_path: Path to image
            conf_threshold: Confidence threshold
            save_result: Whether to save result
        """
        if self.model is None:
            print("❌ Model not loaded.")
            return None
        
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"❌ Cannot load image: {image_path}")
            return None
        
        # Perform inference
        results = self.model(image, conf=conf_threshold, verbose=False)
        result = results[0]
        
        # Process results
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
        
        # Visualize and save results
        if save_result:
            self.visualize_and_save(image, detections, image_path)
        
        return detections
    
    def visualize_and_save(self, image, detections, original_path):
        """Visualize and save results"""
        # Convert OpenCV BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # matplotlib setup
        plt.figure(figsize=(12, 8))
        plt.imshow(image_rgb)
        plt.axis('off')
        
        # Draw detection results
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            conf = detection['confidence']
            cls = detection['class']
            class_name = detection['class_name']
            
            # Bounding box
            width, height = x2 - x1, y2 - y1
            rect = patches.Rectangle(
                (x1, y1), width, height,
                linewidth=2, edgecolor=np.array(self.colors[cls])/255,
                facecolor='none'
            )
            plt.gca().add_patch(rect)
            
            # Label
            label = f'{class_name}: {conf:.2f}'
            plt.text(x1, y1-5, label, 
                    bbox=dict(boxstyle="round,pad=0.3", 
                             facecolor=np.array(self.colors[cls])/255, 
                             alpha=0.7),
                    fontsize=10, color='white', weight='bold')
        
        # Title
        plt.title(f'Detection Results: {len(detections)} objects found', fontsize=14, weight='bold')
        
        # Save
        output_dir = Path("training/yolo/results/detections")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = Path(original_path).stem
        output_path = output_dir / f"{original_name}_detected_{timestamp}.png"
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Result saved: {output_path}")
    
    def predict_folder(self, folder_path, conf_threshold=0.25, max_images=None):
        """
        Inference on all images in folder
        
        Args:
            folder_path: Path to image folder
            conf_threshold: Confidence threshold
            max_images: Maximum number of images to process
        """
        folder = Path(folder_path)
        if not folder.exists():
            print(f"❌ Folder not found: {folder_path}")
            return
        
        # Find image files
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(folder.glob(f"*{ext}"))
            image_files.extend(folder.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"❌ No image files found in: {folder_path}")
            return
        
        # Limit maximum images
        if max_images:
            image_files = image_files[:max_images]
        
        print(f"📁 Processing {len(image_files)} images...")
        
        # Statistics
        total_detections = 0
        class_counts = {0: 0, 1: 0}
        
        for i, image_file in enumerate(image_files):
            print(f"🔍 Processing: {image_file.name} ({i+1}/{len(image_files)})")
            
            detections = self.predict_image(image_file, conf_threshold)
            if detections:
                total_detections += len(detections)
                for det in detections:
                    class_counts[det['class']] += 1
        
        # Summary
        print(f"\n📊 Processing completed!")
        print(f"  Total images: {len(image_files)}")
        print(f"  Total detections: {total_detections}")
        print(f"  Flock detections: {class_counts[0]}")
        print(f"  Airplane detections: {class_counts[1]}")
        print(f"  Results folder: inference_results/")

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
    
    print("🚀 BirdRiskSim YOLO Inference Started")
    print("=" * 50)
    
    # Create inference object
    detector = BirdDetectionInference(args.model)
    
    if detector.model is None:
        return
    
    source_path = Path(args.source)
    
    if source_path.is_file():
        # Single file processing
        print(f"📸 Processing single image: {source_path}")
        detections = detector.predict_image(source_path, args.conf)
        
        if detections:
            print(f"✅ {len(detections)} objects detected:")
            for i, det in enumerate(detections):
                print(f"  {i+1}. {det['class_name']}: {det['confidence']:.3f}")
        else:
            print("❌ No objects detected.")
    
    elif source_path.is_dir():
        # Folder processing
        print(f"📁 Processing folder: {source_path}")
        detector.predict_folder(source_path, args.conf, args.max_images)
    
    else:
        print(f"❌ Path not found: {args.source}")

if __name__ == "__main__":
    main() 