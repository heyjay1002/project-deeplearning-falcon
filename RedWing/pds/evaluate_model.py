#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCN 모델 평가 스크립트
학습된 모델의 성능을 종합적으로 평가
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
import koreanize_matplotlib
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.metrics import precision_recall_fscore_support, roc_curve, auc
from sklearn.metrics import precision_recall_curve, f1_score
from sklearn.preprocessing import label_binarize
import logging
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
from collections import Counter

from config import TCN_CONFIG, GESTURE_CLASSES, PATHS, TRAINING_CONFIG
from model import TCNGestureClassifier
from dataset import GestureDataset

# Create English class names list in order
GESTURE_CLASSES_EN = [GESTURE_CLASSES[i] for i in range(len(GESTURE_CLASSES))]
from torch.utils.data import DataLoader

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_style("whitegrid")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelEvaluator:
    """TCN 모델 종합 평가 클래스"""
    
    def __init__(self, model_path: str = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path or PATHS['model_file']
        self.model = None
        self.test_loader = None
        
        # 결과 저장 폴더
        self.results_dir = Path("evaluation_results")
        self.results_dir.mkdir(exist_ok=True)
        
    def load_model(self):
        """학습된 모델 로드"""
        try:
            self.model = TCNGestureClassifier(
                input_size=TCN_CONFIG['input_size'],
                num_channels=TCN_CONFIG['num_channels'],
                kernel_size=TCN_CONFIG['kernel_size'],
                dropout=TCN_CONFIG['dropout'],
                num_classes=TCN_CONFIG['num_classes']
            )
            
            if Path(self.model_path).exists():
                checkpoint = torch.load(self.model_path, map_location=self.device)
                if 'model_state_dict' in checkpoint:
                    # checkpoint 형태로 저장된 경우
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                else:
                    # state_dict만 저장된 경우
                    self.model.load_state_dict(checkpoint)
                
                self.model.to(self.device)
                self.model.eval()
                logger.info(f"모델 로드 완료: {self.model_path}")
                return True
            else:
                logger.error(f"모델 파일을 찾을 수 없습니다: {self.model_path}")
                return False
                
        except Exception as e:
            logger.error(f"모델 로드 오류: {e}")
            return False
    
    def load_test_data(self):
        """테스트 데이터 로드"""
        try:
            test_dataset = GestureDataset(
                data_root=PATHS['processed_data'],
                split='test',
                test_size=1.0 - TRAINING_CONFIG['train_test_split']
            )
            
            self.test_loader = DataLoader(
                test_dataset,
                batch_size=TRAINING_CONFIG['batch_size'],
                shuffle=False,
                num_workers=2
            )
            
            logger.info(f"테스트 데이터 로드 완료: {len(test_dataset)}개 샘플")
            return True
            
        except Exception as e:
            logger.error(f"테스트 데이터 로드 오류: {e}")
            return False
    
    def evaluate_model(self):
        """모델 성능 평가"""
        if not self.model or not self.test_loader:
            logger.error("모델 또는 데이터가 로드되지 않았습니다")
            return None
        
        all_predictions = []
        all_targets = []
        all_confidences = []
        
        with torch.no_grad():
            for batch_data, batch_targets in self.test_loader:
                batch_data = batch_data.to(self.device)
                batch_targets = batch_targets.to(self.device)
                
                # 예측
                outputs = self.model(batch_data)
                probabilities = torch.softmax(outputs, dim=1)
                predictions = torch.argmax(outputs, dim=1)
                
                # 결과 저장
                all_predictions.extend(predictions.cpu().numpy())
                all_targets.extend(batch_targets.cpu().numpy())
                all_confidences.extend(torch.max(probabilities, dim=1)[0].cpu().numpy())
        
        return {
            'predictions': np.array(all_predictions),
            'targets': np.array(all_targets),
            'confidences': np.array(all_confidences)
        }
    
    def calculate_metrics(self, results):
        """상세 성능 지표 계산"""
        predictions = results['predictions']
        targets = results['targets']
        confidences = results['confidences']
        
        # 기본 지표
        accuracy = accuracy_score(targets, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            targets, predictions, average='weighted'
        )
        
        # 클래스별 지표
        class_report = classification_report(
            targets, predictions,
            target_names=GESTURE_CLASSES_EN,
            output_dict=True
        )
        
        # 신뢰도 통계 (JSON 직렬화를 위해 float 변환)
        confidence_stats = {
            'mean': float(np.mean(confidences)),
            'std': float(np.std(confidences)),
            'min': float(np.min(confidences)),
            'max': float(np.max(confidences))
        }
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'class_report': class_report,
            'confidence_stats': confidence_stats
        }
    
    def plot_confusion_matrix(self, results, save_path=None):
        """Confusion Matrix 시각화"""
        predictions = results['predictions']
        targets = results['targets']
        
        # Confusion Matrix 계산
        cm = confusion_matrix(targets, predictions)
        
        # 시각화
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            cm, 
            annot=True, 
            fmt='d',
            cmap='Blues',
            xticklabels=GESTURE_CLASSES_EN,
            yticklabels=GESTURE_CLASSES_EN
        )
        plt.title('Gesture Recognition Confusion Matrix', fontsize=14, fontweight='bold')
        plt.xlabel('Predicted Gesture', fontsize=12)
        plt.ylabel('Actual Gesture', fontsize=12)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Confusion Matrix saved: {save_path}")
        
        plt.show()
    
    def plot_confidence_distribution(self, results, save_path=None):
        """신뢰도 분포 시각화"""
        confidences = results['confidences']
        predictions = results['predictions']
        
        plt.figure(figsize=(12, 8))
        
        # 전체 신뢰도 히스토그램
        plt.subplot(2, 2, 1)
        plt.hist(confidences, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        plt.title('Overall Confidence Distribution')
        plt.xlabel('Confidence')
        plt.ylabel('Frequency')
        
        # 클래스별 신뢰도 박스플롯
        plt.subplot(2, 2, 2)
        confidence_by_class = [confidences[predictions == i] for i in range(len(GESTURE_CLASSES))]
        plt.boxplot(confidence_by_class, labels=GESTURE_CLASSES_EN)
        plt.title('Confidence Distribution by Class')
        plt.ylabel('Confidence')
        plt.xticks(rotation=45)
        
        # 신뢰도 vs 정확도
        plt.subplot(2, 2, 3)
        correct = (predictions == results['targets'])
        plt.scatter(confidences[correct], [1]*sum(correct), alpha=0.5, label='Correct', color='green')
        plt.scatter(confidences[~correct], [0]*sum(~correct), alpha=0.5, label='Incorrect', color='red')
        plt.title('Confidence vs Correctness')
        plt.xlabel('Confidence')
        plt.ylabel('Correct/Incorrect')
        plt.legend()
        
        # 신뢰도 임계값별 정확도
        plt.subplot(2, 2, 4)
        thresholds = np.arange(0.5, 1.0, 0.05)
        accuracies = []
        for threshold in thresholds:
            mask = confidences >= threshold
            if sum(mask) > 0:
                acc = accuracy_score(results['targets'][mask], predictions[mask])
                accuracies.append(acc)
            else:
                accuracies.append(0)
        
        plt.plot(thresholds, accuracies, marker='o')
        plt.title('Accuracy by Confidence Threshold')
        plt.xlabel('Confidence Threshold')
        plt.ylabel('Accuracy')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Confidence distribution saved: {save_path}")
        
        plt.show()
    
    def plot_roc_curves(self, results, save_path=None):
        """ROC 곡선 시각화 (Multiclass)"""
        predictions = results['predictions']
        targets = results['targets']
        
        # One-hot encode targets
        y_true = label_binarize(targets, classes=list(range(len(GESTURE_CLASSES))))
        y_pred = label_binarize(predictions, classes=list(range(len(GESTURE_CLASSES))))
        
        plt.figure(figsize=(12, 8))
        
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        
        for i in range(len(GESTURE_CLASSES)):
            if i < len(colors):
                color = colors[i]
            else:
                color = np.random.rand(3,)
                
            # Calculate ROC curve
            fpr, tpr, _ = roc_curve(y_true[:, i], y_pred[:, i])
            roc_auc = auc(fpr, tpr)
            
            plt.plot(fpr, tpr, color=color, lw=2,
                    label=f'{GESTURE_CLASSES_EN[i]} (AUC = {roc_auc:.2f})')
        
        plt.plot([0, 1], [0, 1], 'k--', lw=2, label='Random')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curves for Each Gesture Class')
        plt.legend(loc="lower right")
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"ROC curves saved: {save_path}")
        
        plt.show()
    
    def plot_class_performance_comparison(self, results, save_path=None):
        """클래스별 성능 비교 바 차트"""
        predictions = results['predictions']
        targets = results['targets']
        
        # 클래스별 지표 계산
        class_metrics = {}
        for i, class_name in enumerate(GESTURE_CLASSES_EN):
            mask = targets == i
            if np.sum(mask) > 0:
                class_preds = predictions[mask]
                class_accuracy = np.mean(class_preds == i)
                
                # 전체에서 이 클래스에 대한 precision, recall 계산
                tp = np.sum((predictions == i) & (targets == i))
                fp = np.sum((predictions == i) & (targets != i))
                fn = np.sum((predictions != i) & (targets == i))
                
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                class_metrics[class_name] = {
                    'accuracy': class_accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1
                }
        
        # 시각화
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Class-wise Performance Comparison', fontsize=16, fontweight='bold')
        
        metrics_names = ['accuracy', 'precision', 'recall', 'f1_score']
        metric_titles = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        
        for idx, (metric, title) in enumerate(zip(metrics_names, metric_titles)):
            ax = axes[idx // 2, idx % 2]
            
            classes = list(class_metrics.keys())
            values = [class_metrics[cls][metric] for cls in classes]
            
            bars = ax.bar(classes, values, color=['skyblue', 'lightcoral', 'lightgreen', 'orange'])
            ax.set_title(f'{title} by Class')
            ax.set_ylabel(title)
            ax.set_ylim(0, 1.1)
            
            # 값 표시
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{value:.3f}', ha='center', va='bottom')
            
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Class performance comparison saved: {save_path}")
        
        plt.show()
    
    def plot_error_analysis(self, results, save_path=None):
        """오분류 분석 시각화"""
        predictions = results['predictions']
        targets = results['targets']
        confidences = results['confidences']
        
        # 오분류 찾기
        misclassified = predictions != targets
        
        if np.sum(misclassified) == 0:
            print("No misclassifications found!")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Error Analysis', fontsize=16, fontweight='bold')
        
        # 1. 오분류 개수 by 실제 클래스
        ax1 = axes[0, 0]
        error_by_true_class = []
        for i in range(len(GESTURE_CLASSES)):
            errors = np.sum(misclassified & (targets == i))
            error_by_true_class.append(errors)
        
        bars1 = ax1.bar(GESTURE_CLASSES_EN, error_by_true_class, color='lightcoral')
        ax1.set_title('Misclassifications by True Class')
        ax1.set_ylabel('Number of Errors')
        ax1.tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars1, error_by_true_class):
            if value > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                        str(value), ha='center', va='bottom')
        
        # 2. 오분류 개수 by 예측 클래스
        ax2 = axes[0, 1]
        error_by_pred_class = []
        for i in range(len(GESTURE_CLASSES)):
            errors = np.sum(misclassified & (predictions == i))
            error_by_pred_class.append(errors)
        
        bars2 = ax2.bar(GESTURE_CLASSES_EN, error_by_pred_class, color='lightblue')
        ax2.set_title('Misclassifications by Predicted Class')
        ax2.set_ylabel('Number of Errors')
        ax2.tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars2, error_by_pred_class):
            if value > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                        str(value), ha='center', va='bottom')
        
        # 3. 오분류의 신뢰도 분포
        ax3 = axes[1, 0]
        correct_confidences = confidences[~misclassified]
        incorrect_confidences = confidences[misclassified]
        
        ax3.hist(correct_confidences, bins=20, alpha=0.7, label='Correct', color='green', density=True)
        ax3.hist(incorrect_confidences, bins=20, alpha=0.7, label='Incorrect', color='red', density=True)
        ax3.set_title('Confidence Distribution: Correct vs Incorrect')
        ax3.set_xlabel('Confidence')
        ax3.set_ylabel('Density')
        ax3.legend()
        
        # 4. 신뢰도 vs 정확도 (구간별)
        ax4 = axes[1, 1]
        confidence_bins = np.arange(0.0, 1.01, 0.1)
        bin_accuracies = []
        bin_centers = []
        
        for i in range(len(confidence_bins) - 1):
            mask = (confidences >= confidence_bins[i]) & (confidences < confidence_bins[i+1])
            if np.sum(mask) > 0:
                bin_accuracy = np.mean(predictions[mask] == targets[mask])
                bin_accuracies.append(bin_accuracy)
                bin_centers.append((confidence_bins[i] + confidence_bins[i+1]) / 2)
        
        ax4.plot(bin_centers, bin_accuracies, 'bo-', linewidth=2, markersize=8)
        ax4.set_title('Accuracy vs Confidence (Binned)')
        ax4.set_xlabel('Confidence Bin Center')
        ax4.set_ylabel('Accuracy')
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 1.1)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Error analysis saved: {save_path}")
        
        plt.show()
    
    def plot_performance_summary(self, metrics, save_path=None):
        """성능 지표 종합 요약 차트"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Model Performance Summary', fontsize=16, fontweight='bold')
        
        # 1. 전체 성능 지표 레이더 차트
        ax1 = axes[0, 0]
        
        overall_metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        values = [
            metrics['accuracy'],
            metrics['precision'], 
            metrics['recall'],
            metrics['f1_score']
        ]
        
        # 레이더 차트 대신 바 차트 사용 (더 명확함)
        bars = ax1.bar(overall_metrics, values, color=['gold', 'lightblue', 'lightgreen', 'coral'])
        ax1.set_title('Overall Performance Metrics')
        ax1.set_ylabel('Score')
        ax1.set_ylim(0, 1.1)
        
        for bar, value in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                    f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. 신뢰도 통계
        ax2 = axes[0, 1]
        conf_stats = metrics['confidence_stats']
        stats_names = ['Mean', 'Std', 'Min', 'Max']
        stats_values = [conf_stats['mean'], conf_stats['std'], conf_stats['min'], conf_stats['max']]
        
        bars2 = ax2.bar(stats_names, stats_values, color=['purple', 'orange', 'red', 'green'])
        ax2.set_title('Confidence Statistics')
        ax2.set_ylabel('Confidence Value')
        
        for bar, value in zip(bars2, stats_values):
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                    f'{value:.3f}', ha='center', va='bottom')
        
        # 3. 클래스별 지원 수 (Support)
        ax3 = axes[1, 0]
        class_report = metrics['class_report']
        
        supports = []
        for class_name in GESTURE_CLASSES_EN:
            if class_name in class_report:
                supports.append(class_report[class_name]['support'])
            else:
                supports.append(0)
        
        bars3 = ax3.bar(GESTURE_CLASSES_EN, supports, color='lightcyan')
        ax3.set_title('Test Samples per Class')
        ax3.set_ylabel('Number of Samples')
        ax3.tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars3, supports):
            ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                    str(int(value)), ha='center', va='bottom')
        
        # 4. 성능 등급 표시
        ax4 = axes[1, 1]
        
        # 성능 등급 결정
        accuracy = metrics['accuracy']
        if accuracy >= 0.98:
            grade = 'Excellent'
            color = 'green'
        elif accuracy >= 0.95:
            grade = 'Very Good'
            color = 'lightgreen'
        elif accuracy >= 0.90:
            grade = 'Good'
            color = 'yellow'
        elif accuracy >= 0.80:
            grade = 'Fair'
            color = 'orange'
        else:
            grade = 'Poor'
            color = 'red'
        
        ax4.text(0.5, 0.7, f'Model Grade', ha='center', va='center', fontsize=16, fontweight='bold')
        ax4.text(0.5, 0.5, grade, ha='center', va='center', fontsize=24, fontweight='bold', color=color)
        ax4.text(0.5, 0.3, f'Accuracy: {accuracy:.1%}', ha='center', va='center', fontsize=14)
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        
        # 배경 색상 설정
        ax4.add_patch(plt.Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=color, alpha=0.1))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Performance summary saved: {save_path}")
        
        plt.show()
    
    def analyze_misclassifications(self, results):
        """오분류 상세 분석"""
        predictions = results['predictions']
        targets = results['targets']
        confidences = results['confidences']
        
        misclassified = predictions != targets
        
        if np.sum(misclassified) == 0:
            return "No misclassifications found! Perfect performance!"
        
        analysis = []
        analysis.append("=== MISCLASSIFICATION ANALYSIS ===\n")
        
        # 전체 오분류 통계
        total_errors = np.sum(misclassified)
        total_samples = len(predictions)
        error_rate = total_errors / total_samples
        
        analysis.append(f"Total Misclassifications: {total_errors}/{total_samples}")
        analysis.append(f"Error Rate: {error_rate:.1%}\n")
        
        # 클래스별 오분류 매트릭스
        analysis.append("Class-wise Error Matrix:")
        for true_class in range(len(GESTURE_CLASSES)):
            true_name = GESTURE_CLASSES_EN[true_class]
            errors_for_class = misclassified & (targets == true_class)
            
            if np.sum(errors_for_class) > 0:
                analysis.append(f"\n{true_name} misclassified as:")
                pred_classes = predictions[errors_for_class]
                for pred_class in np.unique(pred_classes):
                    count = np.sum(pred_classes == pred_class)
                    pred_name = GESTURE_CLASSES_EN[pred_class]
                    analysis.append(f"  - {pred_name}: {count} times")
        
        # 신뢰도 분석
        analysis.append(f"\nConfidence Analysis:")
        analysis.append(f"Average confidence (correct): {np.mean(confidences[~misclassified]):.3f}")
        analysis.append(f"Average confidence (incorrect): {np.mean(confidences[misclassified]):.3f}")
        
        # 가장 확신하는 오분류
        if np.sum(misclassified) > 0:
            high_conf_errors = misclassified & (confidences > 0.9)
            if np.sum(high_conf_errors) > 0:
                analysis.append(f"\nHigh-confidence errors (>0.9): {np.sum(high_conf_errors)}")
                analysis.append("This suggests potential systematic issues in the model.")
        
        return "\n".join(analysis)
    
    def save_evaluation_report(self, metrics, results, save_path=None):
        """평가 보고서 저장"""
        if not save_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.results_dir / f"evaluation_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'model_path': str(self.model_path),
            'overall_metrics': {
                'accuracy': float(metrics['accuracy']),
                'precision': float(metrics['precision']),
                'recall': float(metrics['recall']),
                'f1_score': float(metrics['f1_score'])
            },
            'confidence_stats': metrics['confidence_stats'],
            'class_report': metrics['class_report']
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Evaluation report saved: {save_path}")
        return save_path
    
    def run_full_evaluation(self):
        """전체 평가 실행"""
        logger.info("=== TCN 모델 종합 평가 시작 ===")
        
        # 1. 모델 및 데이터 로드
        if not self.load_model():
            return False
        
        if not self.load_test_data():
            return False
        
        # 2. 모델 평가
        logger.info("모델 평가 중...")
        results = self.evaluate_model()
        if not results:
            return False
        
        # 3. 성능 지표 계산
        logger.info("성능 지표 계산 중...")
        metrics = self.calculate_metrics(results)
        
        # 4. 결과 출력
        print("\n" + "="*50)
        print("📊 TCN 모델 평가 결과")
        print("="*50)
        print(f"✅ 전체 정확도: {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
        print(f"📈 정밀도: {metrics['precision']:.4f}")
        print(f"📉 재현율: {metrics['recall']:.4f}")
        print(f"🎯 F1-Score: {metrics['f1_score']:.4f}")
        print(f"🔍 평균 신뢰도: {metrics['confidence_stats']['mean']:.4f}")
        print("="*50)
        
        # 5. 상세 분석 및 시각화
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info("상세 시각화 생성 중...")
        
        # Confusion Matrix
        cm_path = self.results_dir / f"confusion_matrix_{timestamp}.png"
        self.plot_confusion_matrix(results, cm_path)
        
        # 신뢰도 분포
        conf_path = self.results_dir / f"confidence_distribution_{timestamp}.png"
        self.plot_confidence_distribution(results, conf_path)
        
        # ROC 곡선
        roc_path = self.results_dir / f"roc_curves_{timestamp}.png"
        self.plot_roc_curves(results, roc_path)
        
        # 클래스별 성능 비교
        class_perf_path = self.results_dir / f"class_performance_{timestamp}.png"
        self.plot_class_performance_comparison(results, class_perf_path)
        
        # 오분류 분석
        error_path = self.results_dir / f"error_analysis_{timestamp}.png"
        self.plot_error_analysis(results, error_path)
        
        # 성능 요약
        summary_path = self.results_dir / f"performance_summary_{timestamp}.png"
        self.plot_performance_summary(metrics, summary_path)
        
        # 6. 오분류 상세 분석
        logger.info("오분류 분석 중...")
        misclass_analysis = self.analyze_misclassifications(results)
        
        # 텍스트 보고서 저장
        text_report_path = self.results_dir / f"misclassification_analysis_{timestamp}.txt"
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(misclass_analysis)
        logger.info(f"Misclassification analysis saved: {text_report_path}")
        
        # 콘솔에 요약 출력
        print("\n" + "="*60)
        print("🔍 MISCLASSIFICATION SUMMARY")
        print("="*60)
        lines = misclass_analysis.split('\n')
        for line in lines[:10]:  # 처음 10줄만 출력
            print(line)
        if len(lines) > 10:
            print("... (더 자세한 내용은 파일을 확인하세요)")
        print("="*60)
        
        # 7. 종합 보고서 저장
        report_path = self.save_evaluation_report(metrics, results)
        
        logger.info("=== 평가 완료 ===")
        return True

if __name__ == "__main__":
    evaluator = ModelEvaluator()
    evaluator.run_full_evaluation() 