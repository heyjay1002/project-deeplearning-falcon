#!/usr/bin/env python3
"""
BirdRiskSim YOLO 학습 결과 시각화 스크립트
학습 완료 후 결과를 종합적으로 분석하고 시각화
"""

import os
import yaml
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from PIL import Image
import cv2
import argparse
from datetime import datetime

plt.style.use('seaborn-v0_8')
# 한글 폰트 설정
try:
    plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'DejaVu Sans', 'sans-serif']
except:
    plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

class YOLOResultVisualizer:
    def __init__(self, run_path):
        """
        Args:
            run_path: 학습 결과 폴더 경로 (runs/train/bird_detection_*)
        """
        self.run_path = Path(run_path)
        self.results_csv = self.run_path / "results.csv"
        self.output_dir = self.run_path / "analysis"
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📊 분석 대상: {self.run_path}")
        print(f"📁 출력 폴더: {self.output_dir}")
    
    def load_results(self):
        """학습 결과 CSV 로드"""
        if not self.results_csv.exists():
            print(f"❌ results.csv 파일을 찾을 수 없습니다: {self.results_csv}")
            return None
        
        try:
            df = pd.read_csv(self.results_csv)
            # 컬럼명 정리 (공백 제거)
            df.columns = df.columns.str.strip()
            print(f"✅ 결과 데이터 로드: {len(df)} epochs")
            return df
        except Exception as e:
            print(f"❌ CSV 로드 실패: {e}")
            return None
    
    def plot_training_curves(self, df):
        """학습 곡선 시각화"""
        print("📈 학습 곡선 생성 중...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('BirdRiskSim YOLO 학습 결과 분석', fontsize=16, fontweight='bold')
        
        # 1. 손실 함수들
        ax1 = axes[0, 0]
        if 'train/box_loss' in df.columns:
            ax1.plot(df['epoch'], df['train/box_loss'], label='Train Box Loss', color='#1f77b4', linewidth=2)
        if 'val/box_loss' in df.columns:
            ax1.plot(df['epoch'], df['val/box_loss'], label='Val Box Loss', color='#ff7f0e', linewidth=2)
        ax1.set_title('Box Loss', fontweight='bold')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 클래스 손실
        ax2 = axes[0, 1]
        if 'train/cls_loss' in df.columns:
            ax2.plot(df['epoch'], df['train/cls_loss'], label='Train Cls Loss', color='#2ca02c', linewidth=2)
        if 'val/cls_loss' in df.columns:
            ax2.plot(df['epoch'], df['val/cls_loss'], label='Val Cls Loss', color='#d62728', linewidth=2)
        ax2.set_title('Classification Loss', fontweight='bold')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. mAP 지표들
        ax3 = axes[0, 2]
        if 'metrics/mAP50(B)' in df.columns:
            ax3.plot(df['epoch'], df['metrics/mAP50(B)'], label='mAP@0.5', color='#9467bd', linewidth=2)
        if 'metrics/mAP50-95(B)' in df.columns:
            ax3.plot(df['epoch'], df['metrics/mAP50-95(B)'], label='mAP@0.5:0.95', color='#17becf', linewidth=2)
        ax3.set_title('Mean Average Precision', fontweight='bold')
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('mAP')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Precision & Recall
        ax4 = axes[1, 0]
        if 'metrics/precision(B)' in df.columns:
            ax4.plot(df['epoch'], df['metrics/precision(B)'], label='Precision', color='#bcbd22', linewidth=2)
        if 'metrics/recall(B)' in df.columns:
            ax4.plot(df['epoch'], df['metrics/recall(B)'], label='Recall', color='#e377c2', linewidth=2)
        ax4.set_title('Precision & Recall', fontweight='bold')
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('Score')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 학습률
        ax5 = axes[1, 1]
        if 'lr/pg0' in df.columns:
            ax5.plot(df['epoch'], df['lr/pg0'], label='Learning Rate', color='#ff7f0e', linewidth=2)
        ax5.set_title('Learning Rate', fontweight='bold')
        ax5.set_xlabel('Epoch')
        ax5.set_ylabel('Learning Rate')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 전체 손실 (개별 loss들의 합으로 계산)
        ax6 = axes[1, 2]
        
        # Total training loss 계산
        if all(col in df.columns for col in ['train/box_loss', 'train/cls_loss', 'train/dfl_loss']):
            total_train_loss = df['train/box_loss'] + df['train/cls_loss'] + df['train/dfl_loss']
            ax6.plot(df['epoch'], total_train_loss, label='Total Training Loss', color='#17becf', linewidth=2)
            
        # Validation loss도 추가
        if all(col in df.columns for col in ['val/box_loss', 'val/cls_loss', 'val/dfl_loss']):
            total_val_loss = df['val/box_loss'] + df['val/cls_loss'] + df['val/dfl_loss']
            ax6.plot(df['epoch'], total_val_loss, label='Total Validation Loss', color='#ff7f0e', linewidth=2, linestyle='--')
            
        ax6.set_title('Total Loss', fontweight='bold')
        ax6.set_xlabel('Epoch')
        ax6.set_ylabel('Loss')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / "training_curves.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ 학습 곡선 저장: {output_path}")
        plt.close()
    
    def create_summary_report(self, df):
        """학습 요약 보고서 생성"""
        print("📋 요약 보고서 생성 중...")
        
        # 최종 성능 지표
        final_epoch = df.iloc[-1]
        best_map50_idx = df['metrics/mAP50(B)'].idxmax() if 'metrics/mAP50(B)' in df.columns else 0
        best_map50_epoch = df.iloc[best_map50_idx]
        
        report = f"""
🎯 BirdRiskSim YOLO 학습 결과 요약
{'='*60}

📊 학습 정보
- 총 에폭: {int(final_epoch['epoch'])}
- 최종 학습률: {final_epoch.get('lr/pg0', 'N/A'):.6f}

🏆 최고 성능 (Epoch {int(best_map50_epoch['epoch'])})
- mAP@0.5: {best_map50_epoch.get('metrics/mAP50(B)', 0):.4f}
- mAP@0.5:0.95: {best_map50_epoch.get('metrics/mAP50-95(B)', 0):.4f}
- Precision: {best_map50_epoch.get('metrics/precision(B)', 0):.4f}
- Recall: {best_map50_epoch.get('metrics/recall(B)', 0):.4f}

📈 최종 성능 (Epoch {int(final_epoch['epoch'])})
- mAP@0.5: {final_epoch.get('metrics/mAP50(B)', 0):.4f}
- mAP@0.5:0.95: {final_epoch.get('metrics/mAP50-95(B)', 0):.4f}
- Precision: {final_epoch.get('metrics/precision(B)', 0):.4f}
- Recall: {final_epoch.get('metrics/recall(B)', 0):.4f}

📉 최종 손실
- Validation Box Loss: {final_epoch.get('val/box_loss', 0):.4f}
- Validation Class Loss: {final_epoch.get('val/cls_loss', 0):.4f}
- Training Total Loss: {(final_epoch.get('train/box_loss', 0) + final_epoch.get('train/cls_loss', 0) + final_epoch.get('train/dfl_loss', 0)):.4f}

🎮 모델 파일
- 최적 모델: weights/best.pt
- 최종 모델: weights/last.pt

생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        report_path = self.output_dir / "training_summary.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 요약 보고서 저장: {report_path}")
        return report
    
    def copy_important_plots(self):
        """중요한 플롯들을 분석 폴더로 복사"""
        print("📋 중요 플롯 복사 중...")
        
        important_files = [
            'results.png',
            'confusion_matrix.png', 
            'F1_curve.png',
            'P_curve.png',
            'R_curve.png',
            'PR_curve.png'
        ]
        
        copied_count = 0
        for file_name in important_files:
            src = self.run_path / file_name
            dst = self.output_dir / file_name
            
            if src.exists():
                import shutil
                shutil.copy2(src, dst)
                copied_count += 1
                print(f"  ✅ {file_name}")
            else:
                print(f"  ⚠️  {file_name} (없음)")
        
        print(f"✅ {copied_count}개 플롯 복사 완료")
    
    def analyze_and_visualize(self):
        """전체 분석 및 시각화 실행"""
        print("🚀 YOLO 학습 결과 분석 시작!")
        print("="*60)
        
        # 1. 데이터 로드
        df = self.load_results()
        if df is None:
            return False
        
        # 2. 학습 곡선 생성
        self.plot_training_curves(df)
        
        # 3. 요약 보고서 생성
        summary = self.create_summary_report(df)
        print(summary)
        
        # 4. 중요 플롯들 복사
        self.copy_important_plots()
        
        print("\n🎉 분석 완료!")
        print(f"📁 결과 폴더: {self.output_dir}")
        print("\n📊 시각화 파일들:")
        for file in self.output_dir.glob("*.png"):
            print(f"  - {file.name}")
        
        return True

def find_latest_run():
    """가장 최근 학습 결과 폴더 찾기"""
    runs_dir = Path("training/yolo/runs/train")
    if not runs_dir.exists():
        return None
    
    # bird_detection_으로 시작하는 폴더들 찾기
    bird_runs = [d for d in runs_dir.iterdir() 
                if d.is_dir() and d.name.startswith('bird_detection_')]
    
    if not bird_runs:
        return None
    
    # 가장 최근 폴더 반환 (이름 기준 정렬)
    return sorted(bird_runs, reverse=True)[0]

def main():
    parser = argparse.ArgumentParser(description='YOLO 학습 결과 시각화')
    parser.add_argument('--run-path', type=str, default=None,
                       help='학습 결과 폴더 경로 (기본값: 최신 결과)')
    
    args = parser.parse_args()
    
    # 학습 결과 폴더 결정
    if args.run_path:
        run_path = Path(args.run_path)
    else:
        run_path = find_latest_run()
        if run_path is None:
            print("❌ 학습 결과 폴더를 찾을 수 없습니다!")
            print("   --run-path 옵션으로 직접 지정하거나")
            print("   먼저 train.py로 학습을 진행하세요.")
            return
    
    if not run_path.exists():
        print(f"❌ 폴더가 존재하지 않습니다: {run_path}")
        return
    
    # 시각화 실행
    visualizer = YOLOResultVisualizer(run_path)
    success = visualizer.analyze_and_visualize()
    
    if success:
        print("\n🚀 다음 단계:")
        print("  1. analysis/ 폴더의 결과 확인")
        print("  2. tensorboard --logdir training/yolo/runs/train")
        print("  3. 웹 브라우저로 http://localhost:6006 접속")

if __name__ == "__main__":
    main() 