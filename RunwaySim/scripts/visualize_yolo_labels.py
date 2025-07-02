#!/usr/bin/env python3
"""
YOLO 라벨링 시각화 스크립트
RunwayRiskSim 프로젝트의 yolo_capture 데이터의 라벨링을 시각화합니다.
"""

import os
import cv2
import numpy as np
import argparse
import glob
from pathlib import Path
import json
from datetime import datetime

# 프로젝트 루트 디렉토리 찾기
project_root = Path(__file__).parent.parent  # scripts/ -> RunwayRiskSim/

class YOLOLabelVisualizer:
    def __init__(self):
        # 클래스 정보 (YoloCaptureManager.cs에서 확인)
        self.class_names = {
            0: "Bird",
            1: "Airplane",
            2: "FOD",
            3: "Animal",
            5: "Fire",
            6: "Car",
            7: "Person"
        }
        
        # 클래스별 색상 (BGR 형식)
        self.class_colors = {
            0: (0, 255, 0),    # 초록색 - Bird
            4: (0, 0, 255),    # 빨간색 - Airplane
        }
        
        # 기본 색상 (알 수 없는 클래스용)
        self.default_color = (0, 255, 255)  # 노란색
    
    def parse_yolo_label(self, label_path):
        """
        YOLO 라벨 파일을 파싱합니다.
        Returns: list of (class_id, center_x, center_y, width, height)
        """
        detections = []
        
        if not os.path.exists(label_path):
            return detections
            
        try:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line:  # 빈 줄 건너뛰기
                    continue
                    
                parts = line.split()
                if len(parts) == 5:
                    class_id = int(parts[0])
                    center_x = float(parts[1])
                    center_y = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    detections.append((class_id, center_x, center_y, width, height))
                    
        except Exception as e:
            print(f"⚠️  라벨 파일 파싱 오류 {label_path}: {e}")
            
        return detections
    
    def draw_detection(self, image, detection, img_width, img_height, show_details=False):
        """
        이미지에 detection 박스를 그립니다.
        """
        class_id, center_x, center_y, width, height = detection
        
        # 정규화된 좌표를 실제 픽셀 좌표로 변환
        center_x_px = int(center_x * img_width)
        center_y_px = int(center_y * img_height)
        width_px = int(width * img_width)
        height_px = int(height * img_height)
        
        # 바운딩 박스 좌표 계산
        x1 = int(center_x_px - width_px / 2)
        y1 = int(center_y_px - height_px / 2)
        x2 = int(center_x_px + width_px / 2)
        y2 = int(center_y_px + height_px / 2)
        
        # 좌표 범위 제한
        x1 = max(0, min(x1, img_width - 1))
        y1 = max(0, min(y1, img_height - 1))
        x2 = max(0, min(x2, img_width - 1))
        y2 = max(0, min(y2, img_height - 1))
        
        # 색상 및 클래스명 선택
        color = self.class_colors.get(class_id, self.default_color)
        class_name = self.class_names.get(class_id, f"Class_{class_id}")
        
        # 바운딩 박스 그리기
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        
        # 중심점 그리기
        cv2.circle(image, (center_x_px, center_y_px), 4, color, -1)
        cv2.circle(image, (center_x_px, center_y_px), 4, (255, 255, 255), 1)
        
        # 라벨 텍스트
        if show_details:
            label_text = f"{class_name} ({center_x:.3f}, {center_y:.3f}) [{width_px}x{height_px}]"
        else:
            label_text = f"{class_name}"
        
        # 텍스트 크기 계산
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)
        
        # 텍스트 배경 그리기
        text_x = x1
        text_y = y1 - 10 if y1 > 30 else y2 + 25
        
        cv2.rectangle(image, 
                     (text_x, text_y - text_height - baseline - 2), 
                     (text_x + text_width + 4, text_y + baseline), 
                     color, -1)
        
        # 텍스트 그리기
        cv2.putText(image, label_text, (text_x + 2, text_y - 2), 
                   font, font_scale, (255, 255, 255), thickness)
        
        return image
    
    def visualize_single_image(self, image_path, label_path, output_path=None, show=False, show_details=False):
        """
        단일 이미지와 라벨을 시각화합니다.
        """
        if not os.path.exists(image_path):
            print(f"❌ 이미지 파일이 없습니다: {image_path}")
            return None
            
        # 이미지 읽기
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
            return None
            
        img_height, img_width = image.shape[:2]
        
        # 라벨 파싱
        detections = self.parse_yolo_label(label_path)
        
        # 각 detection 그리기
        for detection in detections:
            image = self.draw_detection(image, detection, img_width, img_height, show_details)
        
        # 이미지 정보 텍스트 추가
        frame_name = os.path.basename(image_path).split('.')[0]
        info_text = f"Frame: {frame_name} | Objects: {len(detections)} | Size: {img_width}x{img_height}"
        
        # 정보 텍스트 배경
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(info_text, font, font_scale, thickness)
        
        cv2.rectangle(image, (10, 10), (text_width + 20, text_height + baseline + 20), (0, 0, 0), -1)
        cv2.putText(image, info_text, (15, text_height + 15), font, font_scale, (255, 255, 255), thickness)
        
        # 클래스별 통계 표시
        class_counts = {}
        for detection in detections:
            class_id = detection[0]
            class_name = self.class_names.get(class_id, f"Class_{class_id}")
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        y_offset = text_height + 40
        for class_name, count in class_counts.items():
            class_text = f"{class_name}: {count}"
            cv2.putText(image, class_text, (15, y_offset), font, 0.5, (255, 255, 255), 1)
            y_offset += 20
        
        # 출력 처리
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, image)
            
        if show:
            cv2.imshow('YOLO Label Visualization', image)
            key = cv2.waitKey(0)
            cv2.destroyAllWindows()
            return key  # ESC 키 등으로 종료 제어 가능
            
        return image
    
    def visualize_camera_batch(self, camera_path, output_dir=None, max_images=50, show_progress=True):
        """
        카메라 폴더의 여러 이미지를 배치로 시각화합니다.
        """
        camera_name = os.path.basename(camera_path)
        print(f"\n🎥 카메라 {camera_name} 처리 중...")
        
        # 이미지 파일 찾기 (프레임 번호순 정렬)
        image_files = sorted(glob.glob(os.path.join(camera_path, "frame_*.png")), 
                           key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
        
        if not image_files:
            print(f"❌ {camera_path}에 이미지 파일이 없습니다")
            return {}
            
        # 최대 개수 제한
        if len(image_files) > max_images:
            print(f"📊 {len(image_files)}개 이미지 중 최신 {max_images}개만 처리")
            image_files = image_files[-max_images:]  # 최신 이미지들 선택
        
        # 출력 디렉토리 생성
        if output_dir:
            camera_output_dir = os.path.join(output_dir, camera_name)
            os.makedirs(camera_output_dir, exist_ok=True)
        
        stats = {
            "total": 0, 
            "with_objects": 0, 
            "empty": 0,
            "classes": {},
            "total_objects": 0
        }
        
        for i, image_path in enumerate(image_files):
            if show_progress and i % 10 == 0:
                print(f"  진행률: {i+1}/{len(image_files)} ({(i+1)/len(image_files)*100:.1f}%)")
                
            # 대응하는 라벨 파일 경로
            label_path = image_path.replace('.png', '.txt')
            
            # 출력 파일 경로
            output_path = None
            if output_dir:
                output_filename = f"labeled_{os.path.basename(image_path)}"
                output_path = os.path.join(camera_output_dir, output_filename)
            
            # 시각화
            result_image = self.visualize_single_image(image_path, label_path, output_path)
            
            # 통계 업데이트
            if result_image is not None:
                stats["total"] += 1
                detections = self.parse_yolo_label(label_path)
                
                if detections:
                    stats["with_objects"] += 1
                    stats["total_objects"] += len(detections)
                    
                    # 클래스별 통계
                    for detection in detections:
                        class_id = detection[0]
                        class_name = self.class_names.get(class_id, f"Class_{class_id}")
                        stats["classes"][class_name] = stats["classes"].get(class_name, 0) + 1
                else:
                    stats["empty"] += 1
        
        # 통계 출력
        print(f"\n📈 {camera_name} 처리 완료:")
        print(f"   - 총 이미지: {stats['total']}개")
        print(f"   - 객체 포함: {stats['with_objects']}개")
        print(f"   - 빈 프레임: {stats['empty']}개")
        print(f"   - 총 객체 수: {stats['total_objects']}개")
        if stats['total'] > 0:
            print(f"   - 객체 검출률: {stats['with_objects']/stats['total']*100:.1f}%")
            print(f"   - 평균 객체/프레임: {stats['total_objects']/stats['total']:.1f}개")
        
        if stats['classes']:
            print(f"   - 클래스별 분포:")
            for class_name, count in sorted(stats['classes'].items()):
                percentage = count / stats['total_objects'] * 100 if stats['total_objects'] > 0 else 0
                print(f"     * {class_name}: {count}개 ({percentage:.1f}%)")
        
        return stats
    
    def analyze_dataset(self, yolo_capture_path):
        """
        전체 데이터셋을 분석합니다.
        """
        print("🔍 데이터셋 분석 중...")
        
        camera_dirs = [d for d in os.listdir(yolo_capture_path) 
                      if os.path.isdir(os.path.join(yolo_capture_path, d)) and 
                      d.startswith('Fixed_Camera_')]
        
        if not camera_dirs:
            print("❌ 카메라 폴더를 찾을 수 없습니다.")
            return {}
        
        total_stats = {
            "images": 0, 
            "labels": 0, 
            "objects": 0, 
            "empty_frames": 0,
            "classes": {}
        }
        camera_stats = {}
        
        for camera_dir in sorted(camera_dirs):
            camera_path = os.path.join(yolo_capture_path, camera_dir)
            
            # 이미지와 라벨 파일 개수
            images = glob.glob(os.path.join(camera_path, "frame_*.png"))
            labels = glob.glob(os.path.join(camera_path, "frame_*.txt"))
            
            camera_objects = 0
            camera_empty = 0
            camera_classes = {}
            
            # 각 라벨 파일 분석
            for label_path in labels:
                detections = self.parse_yolo_label(label_path)
                if detections:
                    camera_objects += len(detections)
                    for detection in detections:
                        class_id = detection[0]
                        class_name = self.class_names.get(class_id, f"Class_{class_id}")
                        
                        total_stats["classes"][class_name] = total_stats["classes"].get(class_name, 0) + 1
                        camera_classes[class_name] = camera_classes.get(class_name, 0) + 1
                else:
                    camera_empty += 1
            
            camera_stats[camera_dir] = {
                "images": len(images),
                "labels": len(labels),
                "objects": camera_objects,
                "empty_frames": camera_empty,
                "classes": camera_classes
            }
            
            print(f"📹 {camera_dir}:")
            print(f"   - 이미지: {len(images)}개, 라벨: {len(labels)}개")
            print(f"   - 객체: {camera_objects}개, 빈 프레임: {camera_empty}개")
            if len(labels) > 0:
                print(f"   - 검출률: {(len(labels)-camera_empty)/len(labels)*100:.1f}%")
            
            total_stats["images"] += len(images)
            total_stats["labels"] += len(labels)
            total_stats["objects"] += camera_objects
            total_stats["empty_frames"] += camera_empty
        
        print(f"\n📊 전체 데이터셋 통계:")
        print(f"   - 총 이미지: {total_stats['images']}개")
        print(f"   - 총 라벨: {total_stats['labels']}개")
        print(f"   - 총 객체: {total_stats['objects']}개")
        print(f"   - 빈 프레임: {total_stats['empty_frames']}개")
        
        if total_stats['labels'] > 0:
            detection_rate = (total_stats['labels']-total_stats['empty_frames'])/total_stats['labels']*100
            print(f"   - 객체 검출률: {detection_rate:.1f}%")
            
        if total_stats['objects'] > 0:
            avg_objects = total_stats['objects']/total_stats['labels']
            print(f"   - 평균 객체/프레임: {avg_objects:.1f}개")
        
        if total_stats['classes']:
            print(f"\n🏷️  클래스별 분포:")
            for class_name, count in sorted(total_stats['classes'].items()):
                percentage = count / total_stats['objects'] * 100 if total_stats['objects'] > 0 else 0
                print(f"   - {class_name}: {count}개 ({percentage:.1f}%)")
        
        return {"total": total_stats, "cameras": camera_stats}
    
    def create_summary_report(self, stats, output_dir):
        """
        분석 결과를 JSON 파일로 저장합니다.
        """
        if not output_dir:
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report = {
            "timestamp": timestamp,
            "analysis_time": datetime.now().isoformat(),
            "statistics": stats
        }
        
        report_path = os.path.join(output_dir, f"yolo_analysis_report_{timestamp}.json")
        os.makedirs(output_dir, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 분석 리포트 저장: {report_path}")

def main():
    parser = argparse.ArgumentParser(description='YOLO 라벨링 시각화 도구 - RunwayRiskSim')
    parser.add_argument('--input', '-i', default='data/yolo_capture', 
                       help='yolo_capture 디렉토리 경로 (기본값: data/yolo_capture)')
    parser.add_argument('--output', '-o', default='data/yolo_visualization', 
                       help='시각화된 이미지 출력 디렉토리 (기본값: data/yolo_visualization)')
    parser.add_argument('--camera', '-c', 
                       help='특정 카메라만 처리 (예: Fixed_Camera_A)')
    parser.add_argument('--max-images', '-m', type=int, default=50, 
                       help='카메라당 최대 처리 이미지 수 (기본값: 50)')
    parser.add_argument('--analyze-only', '-a', action='store_true', 
                       help='분석만 수행 (시각화 안함)')
    parser.add_argument('--show', '-s', action='store_true', 
                       help='시각화 결과를 화면에 표시')
    parser.add_argument('--details', '-d', action='store_true',
                       help='상세 정보 표시 (좌표, 크기 등)')
    parser.add_argument('--no-save', action='store_true',
                       help='이미지 저장하지 않음')
    
    args = parser.parse_args()
    
    # 절대 경로로 변환
    if not os.path.isabs(args.input):
        args.input = os.path.join(project_root, args.input)
    if not os.path.isabs(args.output):
        args.output = os.path.join(project_root, args.output)
    
    visualizer = YOLOLabelVisualizer()
    
    # 입력 경로 확인
    if not os.path.exists(args.input):
        print(f"❌ 입력 디렉토리가 없습니다: {args.input}")
        return
    
    print(f"📁 입력 디렉토리: {args.input}")
    if not args.no_save:
        print(f"📁 출력 디렉토리: {args.output}")
    
    # 데이터셋 분석
    stats = visualizer.analyze_dataset(args.input)
    
    # 분석 결과 저장
    if not args.no_save:
        visualizer.create_summary_report(stats, args.output)
    
    if args.analyze_only:
        return
    
    # 출력 디렉토리 생성
    output_dir = None if args.no_save else args.output
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 특정 카메라 처리
    if args.camera:
        camera_path = os.path.join(args.input, args.camera)
        if os.path.exists(camera_path):
            print(f"\n🎯 특정 카메라 처리: {args.camera}")
            visualizer.visualize_camera_batch(camera_path, output_dir, args.max_images)
        else:
            print(f"❌ 카메라 디렉토리가 없습니다: {camera_path}")
    else:
        # 모든 카메라 처리
        camera_dirs = [d for d in os.listdir(args.input) 
                      if os.path.isdir(os.path.join(args.input, d)) and 
                      d.startswith('Fixed_Camera_')]
        
        if not camera_dirs:
            print("❌ 처리할 카메라 폴더를 찾을 수 없습니다.")
            return
        
        print(f"\n🎬 총 {len(camera_dirs)}개 카메라 처리 시작")
        
        for camera_dir in sorted(camera_dirs):
            camera_path = os.path.join(args.input, camera_dir)
            try:
                visualizer.visualize_camera_batch(camera_path, output_dir, args.max_images)
            except KeyboardInterrupt:
                print("\n⏹️  사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ {camera_dir} 처리 중 오류: {e}")
                continue
    
    print(f"\n🎉 처리 완료!")
    if output_dir:
        print(f"📁 결과 확인: {output_dir}")

if __name__ == "__main__":
    main() 