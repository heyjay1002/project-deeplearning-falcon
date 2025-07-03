#!/usr/bin/env python3
"""
BirdRiskSim YOLO 실시간 학습 모니터링
학습 중 실시간으로 진행 상황을 모니터링하고 시각화
"""

import time
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
from datetime import datetime
import signal
import sys

class TrainingMonitor:
    def __init__(self, run_path=None, refresh_interval=10):
        """
        Args:
            run_path: 모니터링할 학습 폴더 경로
            refresh_interval: 새로고침 간격 (초)
        """
        self.refresh_interval = refresh_interval
        self.run_path = self.find_active_run() if run_path is None else Path(run_path)
        self.running = True
        
        # 종료 시그널 처리
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print(f"📊 모니터링 대상: {self.run_path}")
        print(f"🔄 새로고침 간격: {refresh_interval}초")
        print("   (Ctrl+C로 종료)")
    
    def signal_handler(self, sig, frame):
        """종료 시그널 처리"""
        print("\n⚠️  모니터링을 종료합니다...")
        self.running = False
        sys.exit(0)
    
    def find_active_run(self):
        """활성 학습 폴더 찾기"""
        runs_dir = Path("training/yolo/runs/train")
        if not runs_dir.exists():
            return None
        
        # 가장 최근 bird_detection_ 폴더
        bird_runs = [d for d in runs_dir.iterdir() 
                    if d.is_dir() and d.name.startswith('bird_detection_')]
        
        if not bird_runs:
            return None
        
        return sorted(bird_runs, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    
    def load_current_results(self):
        """현재 결과 로드"""
        if not self.run_path or not self.run_path.exists():
            return None
        
        results_csv = self.run_path / "results.csv"
        if not results_csv.exists():
            return None
        
        try:
            df = pd.read_csv(results_csv)
            df.columns = df.columns.str.strip()
            return df
        except:
            return None
    
    def create_live_plot(self, df):
        """실시간 플롯 생성"""
        if df is None or len(df) == 0:
            return
        
        plt.ion()  # 인터랙티브 모드
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'🎯 BirdRiskSim 실시간 학습 모니터링 - Epoch {int(df.iloc[-1]["epoch"])}', 
                    fontsize=14, fontweight='bold')
        
        # 1. 손실 함수
        ax1 = axes[0, 0]
        if 'train/box_loss' in df.columns and 'val/box_loss' in df.columns:
            ax1.plot(df['epoch'], df['train/box_loss'], 'b-', label='Train Loss', linewidth=2)
            ax1.plot(df['epoch'], df['val/box_loss'], 'r-', label='Val Loss', linewidth=2)
        ax1.set_title('📉 Box Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. mAP 지표
        ax2 = axes[0, 1]
        if 'metrics/mAP50(B)' in df.columns:
            ax2.plot(df['epoch'], df['metrics/mAP50(B)'], 'g-', label='mAP@0.5', linewidth=2)
        if 'metrics/mAP50-95(B)' in df.columns:
            ax2.plot(df['epoch'], df['metrics/mAP50-95(B)'], 'm-', label='mAP@0.5:0.95', linewidth=2)
        ax2.set_title('🎯 mAP')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('mAP')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Precision & Recall
        ax3 = axes[1, 0]
        if 'metrics/precision(B)' in df.columns:
            ax3.plot(df['epoch'], df['metrics/precision(B)'], 'c-', label='Precision', linewidth=2)
        if 'metrics/recall(B)' in df.columns:
            ax3.plot(df['epoch'], df['metrics/recall(B)'], 'y-', label='Recall', linewidth=2)
        ax3.set_title('📊 Precision & Recall')
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('Score')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 학습률
        ax4 = axes[1, 1]
        if 'lr/pg0' in df.columns:
            ax4.plot(df['epoch'], df['lr/pg0'], 'orange', linewidth=2)
        ax4.set_title('📈 Learning Rate')
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('LR')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.draw()
        plt.pause(0.1)
    
    def print_current_status(self, df):
        """현재 상태 출력"""
        if df is None or len(df) == 0:
            print("📊 아직 학습 데이터가 없습니다...")
            return
        
        latest = df.iloc[-1]
        epoch = int(latest['epoch'])
        
        # 최고 성능 찾기
        best_map50 = df['metrics/mAP50(B)'].max() if 'metrics/mAP50(B)' in df.columns else 0
        
        print(f"\n📊 현재 상태 (Epoch {epoch}) - {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        print(f"🎯 mAP@0.5: {latest.get('metrics/mAP50(B)', 0):.4f} (최고: {best_map50:.4f})")
        print(f"📈 mAP@0.5:0.95: {latest.get('metrics/mAP50-95(B)', 0):.4f}")
        print(f"🎨 Precision: {latest.get('metrics/precision(B)', 0):.4f}")
        print(f"🔍 Recall: {latest.get('metrics/recall(B)', 0):.4f}")
        print(f"📉 Box Loss: {latest.get('val/box_loss', 0):.4f}")
        print(f"🏷️  Cls Loss: {latest.get('val/cls_loss', 0):.4f}")
        print(f"⚡ 학습률: {latest.get('lr/pg0', 0):.6f}")
    
    def start_monitoring(self):
        """모니터링 시작"""
        print("🚀 실시간 모니터링 시작!")
        print("="*60)
        
        if not self.run_path:
            print("❌ 활성 학습 폴더를 찾을 수 없습니다!")
            return
        
        last_epoch = -1
        
        while self.running:
            try:
                df = self.load_current_results()
                
                if df is not None and len(df) > 0:
                    current_epoch = int(df.iloc[-1]['epoch'])
                    
                    # 새로운 에폭이 있을 때만 업데이트
                    if current_epoch > last_epoch:
                        self.print_current_status(df)
                        self.create_live_plot(df)
                        last_epoch = current_epoch
                
                time.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️  오류 발생: {e}")
                time.sleep(self.refresh_interval)
        
        print("\n✅ 모니터링 종료")

def main():
    parser = argparse.ArgumentParser(description='YOLO 실시간 학습 모니터링')
    parser.add_argument('--run-path', type=str, default=None,
                       help='모니터링할 학습 폴더 경로')
    parser.add_argument('--interval', type=int, default=10,
                       help='새로고침 간격 (초, 기본값: 10)')
    
    args = parser.parse_args()
    
    monitor = TrainingMonitor(args.run_path, args.interval)
    monitor.start_monitoring()

if __name__ == "__main__":
    main() 