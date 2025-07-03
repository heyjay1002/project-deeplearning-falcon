#!/usr/bin/env python3
"""
🎯 수정된 BirdRiskSim 위험도 데모 (타임스탬프 기반 동기화)
"""
import cv2
import json
import numpy as np
from pathlib import Path
import os

class FixedRiskDemo:
    def __init__(self):
        # 위험도 레벨별 색상 (BGR)
        self.risk_colors = {
            'BR_LOW': (0, 255, 0),      # 초록색
            'BR_MEDIUM': (0, 165, 255), # 주황색  
            'BR_HIGH': (0, 0, 255),     # 빨간색
        }
        
    def load_risk_data(self, log_file):
        """위험도 로그 데이터 로드"""
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_frame_timestamp(self, frame_file):
        """프레임 파일의 생성 시간 가져오기"""
        return os.path.getmtime(frame_file)
    
    def draw_detection_box(self, frame, detection):
        """YOLO 감지 박스 그리기"""
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class_name']
        
        # 박스 좌표
        x1, y1, x2, y2 = map(int, bbox)
        
        # 클래스별 색상 - 더 선명하게
        if class_name == 'Airplane':
            color = (0, 255, 255)  # 노란색 (더 두껍게)
            thickness = 4
        else:
            color = (255, 0, 255)  # 자홍색 (더 두껍게)  
            thickness = 4
        
        # 박스 그리기
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        
        # 라벨 배경 그리기
        label = f"{class_name} {confidence:.2f}"
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(frame, (x1, y1-h-15), (x1+w+10, y1), color, -1)
        cv2.putText(frame, label, (x1+5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
    
    def draw_top_bar_only(self, frame):
        """상단 검은 바만 그리기"""
        bar_height = 80
        cv2.rectangle(frame, (0, 0), (frame.shape[1], bar_height), (0, 0, 0), -1)
    
    def draw_risk_info_only(self, frame, risk_data):
        """위험도 정보만 표시 (카메라 A용)"""
        if not risk_data:
            return
            
        # 위험도 정보 추출
        risk_level = risk_data.get('risk_level', 'BR_LOW')
        distance = risk_data.get('hybrid_distance', 0)
        
        # 색상 선택
        color = self.risk_colors.get(risk_level, (128,128,128))
        
        # 상단 위험도 바
        bar_height = 80
        cv2.rectangle(frame, (0, 0), (frame.shape[1], bar_height), (0, 0, 0), -1)
        
        # 위험도 레벨 표시 (중앙 배치)
        level_text = f"RISK: {risk_level}"
        text_size = cv2.getTextSize(level_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 4)[0]
        center_x = (frame.shape[1] - text_size[0]) // 2
        cv2.putText(frame, level_text, (center_x, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 4)
        
        # 거리 정보 (우상단 배치)
        distance_text = f"DISTANCE: {distance:.1f}m"
        cv2.putText(frame, distance_text, (frame.shape[1] - 250, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 3)
    
    def draw_minimap_and_info(self, frame, risk_data, frame_info=""):
        """미니맵과 위치 정보 표시 (카메라 B용)"""
        if not risk_data:
            return
            
        # 위험도 정보 추출
        distance = risk_data.get('hybrid_distance', 0)
        airplane_pos = risk_data.get('airplane_position', ['0', '0'])
        flock_pos = risk_data.get('flock_position', ['0', '0'])
        
        # 상단 검은 바
        bar_height = 80
        cv2.rectangle(frame, (0, 0), (frame.shape[1], bar_height), (0, 0, 0), -1)
        
        # 🎯 실시간 위치 시각화 미니맵 (우상단)
        self.draw_position_minimap(frame, airplane_pos, flock_pos, distance)
        
        # 텍스트 위치 정보 (우측 하단)
        y_pos = frame.shape[0] - 60
        if airplane_pos and len(airplane_pos) >= 2:
            airplane_text = f"AIRPLANE: ({float(airplane_pos[0]):.1f}, {float(airplane_pos[1]):.1f})"
            cv2.putText(frame, airplane_text, (frame.shape[1]-450, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)  # 파란색
        
        if flock_pos and len(flock_pos) >= 2:
            flock_text = f"FLOCK: ({float(flock_pos[0]):.1f}, {float(flock_pos[1]):.1f})"
            cv2.putText(frame, flock_text, (frame.shape[1]-450, y_pos + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)  # 빨간색
        
        # Frame 정보 (좌하단)
        if frame_info:
            cv2.putText(frame, frame_info, (20, frame.shape[0]-20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    
    def draw_position_minimap(self, frame, airplane_pos, flock_pos, actual_distance):
        """실시간 위치 시각화 미니맵"""
        # 미니맵 설정
        minimap_size = 200
        minimap_x = frame.shape[1] - minimap_size - 20  # 우측 여백
        minimap_y = 100  # 위험도 바 아래
        
        # 미니맵 배경 (반투명 검은색)
        overlay = frame.copy()
        cv2.rectangle(overlay, (minimap_x, minimap_y), 
                     (minimap_x + minimap_size, minimap_y + minimap_size), 
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # 미니맵 테두리
        cv2.rectangle(frame, (minimap_x, minimap_y), 
                     (minimap_x + minimap_size, minimap_y + minimap_size), 
                     (255, 255, 255), 2)
        
        # 미니맵 제목
        cv2.putText(frame, "POSITION MAP", (minimap_x + 10, minimap_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 좌표 범위 설정 (실제 데이터에 맞게 조정 필요)
        coord_range = 1000  # -500 ~ +500 범위로 가정
        
        # 중심선 그리기
        center_x = minimap_x + minimap_size // 2
        center_y = minimap_y + minimap_size // 2
        
        # 가로 중심선
        cv2.line(frame, (minimap_x + 10, center_y), 
                (minimap_x + minimap_size - 10, center_y), (100, 100, 100), 1)
        # 세로 중심선  
        cv2.line(frame, (center_x, minimap_y + 10), 
                (center_x, minimap_y + minimap_size - 10), (100, 100, 100), 1)
        
        # 좌표 변환 함수
        def world_to_minimap(pos):
            if not pos or len(pos) < 2:
                return None
            try:
                x, y = float(pos[0]), float(pos[1])
                # 좌표를 미니맵 좌표로 변환
                map_x = int(center_x + (x / coord_range) * (minimap_size // 2 - 20))
                map_y = int(center_y - (y / coord_range) * (minimap_size // 2 - 20))  # Y축 뒤집기
                
                # 경계 체크
                map_x = max(minimap_x + 5, min(minimap_x + minimap_size - 5, map_x))
                map_y = max(minimap_y + 5, min(minimap_y + minimap_size - 5, map_y))
                
                return (map_x, map_y)
            except:
                return None
        
        # 비행기 위치 표시 (파란 원)
        airplane_map_pos = world_to_minimap(airplane_pos)
        if airplane_map_pos:
            cv2.circle(frame, airplane_map_pos, 8, (255, 255, 0), -1)  # 노란색
            cv2.circle(frame, airplane_map_pos, 8, (0, 0, 0), 2)  # 검은 테두리
            cv2.putText(frame, "A", (airplane_map_pos[0] - 5, airplane_map_pos[1] + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # 새떼 위치 표시 (빨간 원)
        flock_map_pos = world_to_minimap(flock_pos)
        if flock_map_pos:
            cv2.circle(frame, flock_map_pos, 8, (0, 0, 255), -1)  # 빨간색
            cv2.circle(frame, flock_map_pos, 8, (255, 255, 255), 2)  # 흰 테두리
            cv2.putText(frame, "B", (flock_map_pos[0] - 5, flock_map_pos[1] + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 거리 표시 (두 점 사이의 선)
        if airplane_map_pos and flock_map_pos:
            cv2.line(frame, airplane_map_pos, flock_map_pos, (255, 255, 255), 2)
            
            # 중점에 거리 표시 (실제 hybrid_distance 사용)
            mid_x = (airplane_map_pos[0] + flock_map_pos[0]) // 2
            mid_y = (airplane_map_pos[1] + flock_map_pos[1]) // 2
            
            # 실제 hybrid_distance 값 사용 (동기화)
            cv2.putText(frame, f"{actual_distance:.0f}m", (mid_x - 15, mid_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def draw_risk_timeline_graph(self, combined_frame, risk_data, frame_num, total_frames, risk_history):
        """📈 실시간 위험도 타임라인 그래프 그리기"""
        graph_height = 120
        frame_height, frame_width = combined_frame.shape[:2]
        
        # 그래프 영역 (어두운 배경)
        graph_area = np.zeros((graph_height, frame_width, 3), dtype=np.uint8)
        graph_area.fill(20)  # 매우 어두운 배경
        
        # 상단 구분선
        cv2.line(graph_area, (0, 0), (frame_width, 0), (100, 100, 100), 2)
        
        # 현재 위험도 데이터 추가
        if risk_data:
            risk_level = risk_data.get('risk_level', 'BR_LOW')
            distance = risk_data.get('hybrid_distance', 0)
            
            # 위험도를 숫자로 변환 (그래프용)
            risk_value = {'BR_LOW': 1, 'BR_MEDIUM': 2, 'BR_HIGH': 3}.get(risk_level, 1)
            
            # 히스토리에 추가
            risk_history.append({
                'frame': frame_num,
                'risk_level': risk_level,
                'risk_value': risk_value,
                'distance': distance
            })
            
            # 히스토리 길이 제한 (최근 200프레임만 유지)
            if len(risk_history) > 200:
                risk_history.pop(0)
        
        # 그래프 그리기 영역 설정
        graph_margin = 50
        graph_x = graph_margin
        graph_y = 20
        graph_w = frame_width - (graph_margin * 2)
        graph_h = graph_height - 40
        
        # 그래프 배경 (격자)
        cv2.rectangle(graph_area, (graph_x, graph_y), (graph_x + graph_w, graph_y + graph_h), (40, 40, 40), 1)
        
        # Y축 격자선 (위험도 레벨)
        for i in range(1, 4):  # LOW, MEDIUM, HIGH
            y = int(graph_y + graph_h - (i / 3.0) * graph_h)
            cv2.line(graph_area, (graph_x, y), (graph_x + graph_w, y), (60, 60, 60), 1)
            
            # Y축 라벨
            level_text = ['', 'LOW', 'MED', 'HIGH'][i]
            color = [(0,255,0), (0,165,255), (0,0,255)][i-1]
            cv2.putText(graph_area, level_text, (5, y + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # 타임라인 그래프 그리기
        if len(risk_history) > 1:
            # X축 범위 계산
            min_frame = min(item['frame'] for item in risk_history)
            max_frame = max(item['frame'] for item in risk_history)
            frame_range = max(max_frame - min_frame, 1)
            
            # 이전 점 저장용
            prev_x, prev_y = None, None
            
            for i, item in enumerate(risk_history):
                # X 좌표 (시간축)
                x_ratio = (item['frame'] - min_frame) / frame_range
                x = int(graph_x + x_ratio * graph_w)
                
                # Y 좌표 (위험도)
                y_ratio = item['risk_value'] / 3.0
                y = int(graph_y + graph_h - y_ratio * graph_h)
                
                # 위험도별 색상
                color = {1: (0,255,0), 2: (0,165,255), 3: (0,0,255)}.get(item['risk_value'], (128,128,128))
                
                # 점 그리기
                cv2.circle(graph_area, (x, y), 3, color, -1)
                
                # 선 연결
                if prev_x is not None and prev_y is not None:
                    cv2.line(graph_area, (prev_x, prev_y), (x, y), color, 2)
                
                prev_x, prev_y = x, y
            
            # 현재 프레임 표시 (세로선)
            if risk_history:
                current_frame = risk_history[-1]['frame']
                current_x_ratio = (current_frame - min_frame) / frame_range
                current_x = int(graph_x + current_x_ratio * graph_w)
                cv2.line(graph_area, (current_x, graph_y), (current_x, graph_y + graph_h), (255, 255, 255), 2)
        
        # 좌측 정보 패널
        info_panel_w = 200
        cv2.rectangle(graph_area, (0, 0), (info_panel_w, graph_height), (0, 0, 0), -1)
        cv2.line(graph_area, (info_panel_w, 0), (info_panel_w, graph_height), (100, 100, 100), 1)
        
        # 현재 상태 정보
        cv2.putText(graph_area, "RISK TIMELINE", (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        
        if risk_data:
            # 현재 위험도
            current_risk = risk_data.get('risk_level', 'BR_LOW')
            risk_color = self.risk_colors.get(current_risk, (128,128,128))
            cv2.putText(graph_area, f"Current: {current_risk}", (10, 45), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 2)
            
            # 현재 거리
            distance = risk_data.get('hybrid_distance', 0)
            cv2.putText(graph_area, f"Distance: {distance:.1f}m", (10, 65), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
            
            # 방향성
            direction = risk_data.get('direction_text', 'Unknown')
            direction_color = (0, 255, 0) if direction == '멀어짐' else (0, 165, 255)
            cv2.putText(graph_area, f"Direction: {direction}", (10, 85), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, direction_color, 1)
        
        # 진행률 정보
        progress = (frame_num / total_frames) * 100 if total_frames > 0 else 0
        cv2.putText(graph_area, f"Progress: {progress:.1f}%", (10, 105), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
        
        # 우측 통계 정보
        stats_x = frame_width - 250
        cv2.putText(graph_area, "STATISTICS", (stats_x, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        
        if risk_history:
            # 위험도 분포 계산
            high_count = sum(1 for item in risk_history if item['risk_value'] == 3)
            medium_count = sum(1 for item in risk_history if item['risk_value'] == 2)
            low_count = sum(1 for item in risk_history if item['risk_value'] == 1)
            total_count = len(risk_history)
            
            if total_count > 0:
                cv2.putText(graph_area, f"HIGH: {high_count} ({high_count/total_count*100:.1f}%)", 
                           (stats_x, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)
                cv2.putText(graph_area, f"MED:  {medium_count} ({medium_count/total_count*100:.1f}%)", 
                           (stats_x, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,165,255), 1)
                cv2.putText(graph_area, f"LOW:  {low_count} ({low_count/total_count*100:.1f}%)", 
                           (stats_x, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)
                
                # 평균 거리
                avg_distance = np.mean([item['distance'] for item in risk_history])
                cv2.putText(graph_area, f"Avg Dist: {avg_distance:.1f}m", 
                           (stats_x, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,0), 1)
        
        return np.vstack((combined_frame, graph_area))

    def match_frames_by_timestamp(self, frame_files, risk_data_list, delay_offset=0.0):
        """타임스탬프 기반으로 프레임과 위험도 데이터 매칭"""
        print(f"🔄 타임스탬프 기반 매칭 시작 (delay_offset: {delay_offset}초)...")
        
        # 프레임 파일들의 타임스탬프 수집
        frame_timestamps = []
        for frame_file in frame_files:
            timestamp = self.get_frame_timestamp(frame_file)
            frame_timestamps.append((timestamp, frame_file))
        
        # 타임스탬프 정렬
        frame_timestamps.sort()
        print(f"📹 프레임 시간 범위: {len(frame_timestamps)}개 파일")
        
        # 위험도 데이터의 타임스탬프와 매칭
        matched_frames = []
        
        for entry in risk_data_list:
            if not entry.get('risk_data'):
                continue
                
            # 로그 타임스탬프 (Unix timestamp)
            log_timestamp = entry.get('timestamp', 0)
            if log_timestamp == 0:
                continue
            
            # delay_offset 적용 (초 단위)
            adjusted_timestamp = log_timestamp + delay_offset
            
            # 가장 가까운 프레임 찾기
            best_match = None
            min_diff = float('inf')
            
            for frame_timestamp, frame_file in frame_timestamps:
                time_diff = abs(frame_timestamp - adjusted_timestamp)
                if time_diff < min_diff:
                    min_diff = time_diff
                    best_match = (frame_file, entry, time_diff)
            
            # 시간 차이가 5초 이내인 경우만 매칭
            if best_match and best_match[2] < 5.0:
                matched_frames.append((best_match[0], best_match[1], best_match[2]))
        
        # 중복 제거 (frame_file 기준) 및 정렬
        seen_frames = set()
        unique_frames = []
        for frame_file, entry, time_diff in matched_frames:
            if frame_file not in seen_frames:
                seen_frames.add(frame_file)
                unique_frames.append((frame_file, entry, time_diff))
        
        matched_frames = sorted(unique_frames, key=lambda x: x[2])
        
        print(f"✅ 타임스탬프 매칭 완료: {len(matched_frames)}개")
        if matched_frames:
            print(f"   평균 시간 차이: {np.mean([x[2] for x in matched_frames]):.3f}초")
            print(f"   최대 시간 차이: {max([x[2] for x in matched_frames]):.3f}초")
        
        return matched_frames

    def create_smooth_demo_video(self, recording_path, log_file, output_path, delay_offset=0.0):
        """부드러운 재생을 위한 연속 프레임 기반 데모 영상 생성 (카메라 A+B 동시 표시)"""
        print(f"🎬 부드러운 위험도 데모 영상 생성 중...")
        
        # 위험도 데이터 로드
        risk_data_list = self.load_risk_data(log_file)
        print(f"📊 로드된 위험도 데이터: {len(risk_data_list)}개 프레임")
        
        # 📈 위험도 히스토리 초기화 (타임라인 그래프용)
        risk_history = []
        
        # 카메라 A와 B 경로 확인
        camera_a_path = Path(recording_path) / "Fixed_Camera_A"
        camera_b_path = Path(recording_path) / "Fixed_Camera_B"
        
        if not camera_a_path.exists():
            print(f"❌ 카메라 A 폴더를 찾을 수 없습니다: {camera_a_path}")
            return False
        if not camera_b_path.exists():
            print(f"❌ 카메라 B 폴더를 찾을 수 없습니다: {camera_b_path}")
            return False
        
        # 실제 프레임 파일 목록 가져오기 (카메라 A 기준)
        frame_files_a = sorted(list(camera_a_path.glob("frame_*.jpg")))
        frame_files_b = sorted(list(camera_b_path.glob("frame_*.jpg")))
        
        if not frame_files_a or not frame_files_b:
            print(f"❌ 프레임 파일이 없습니다: A={len(frame_files_a)}, B={len(frame_files_b)}")
            return False
        
        print(f"📹 발견된 프레임 파일: A={len(frame_files_a)}개, B={len(frame_files_b)}개")
        print(f"   범위: {frame_files_a[0].name} ~ {frame_files_a[-1].name}")
        
        # 🔧 타임스탬프 기반 매칭 (카메라 A 기준)
        matched_frames = self.match_frames_by_timestamp(frame_files_a, risk_data_list, delay_offset)
        
        if not matched_frames:
            print("❌ 매칭된 프레임이 없습니다!")
            return False
        
        # 매칭된 프레임들을 프레임 번호 순으로 정렬 (시간이 아닌 연속성 기준)
        frame_number_map = {}
        for frame_file, frame_data, time_diff in matched_frames:
            # frame_000123.jpg에서 123 추출
            frame_num = int(frame_file.stem.split('_')[-1])
            frame_number_map[frame_num] = (frame_file, frame_data, time_diff)
        
        # 연속된 프레임 번호로 정렬
        sorted_frame_nums = sorted(frame_number_map.keys())
        print(f"🔄 연속 프레임 범위: {sorted_frame_nums[0]} ~ {sorted_frame_nums[-1]}")
        
        # 빈 프레임 구간 채우기 (부드러운 재생을 위해)
        continuous_frames = []
        last_data = None
        
        for i in range(sorted_frame_nums[0], sorted_frame_nums[-1] + 1):
            if i in frame_number_map:
                # 매칭된 데이터가 있는 프레임
                frame_file_a, frame_data, time_diff = frame_number_map[i]
                frame_file_b = camera_b_path / f"frame_{i:06d}.jpg"
                continuous_frames.append((frame_file_a, frame_file_b, frame_data, time_diff, True))  # True = 실제 데이터
                last_data = frame_data
            else:
                # 빈 프레임은 이전 데이터 재사용 (부드러운 전환)
                frame_file_a = camera_a_path / f"frame_{i:06d}.jpg"
                frame_file_b = camera_b_path / f"frame_{i:06d}.jpg"
                if frame_file_a.exists() and frame_file_b.exists():
                    continuous_frames.append((frame_file_a, frame_file_b, last_data, 0.0, False))  # False = 보간 데이터
        
        print(f"📹 연속 프레임 생성: {len(continuous_frames)}개 (보간 포함)")
        
        # 첫 번째 프레임으로 크기 확인
        first_frame_a, first_frame_b, _, _, _ = continuous_frames[0]
        
        if not first_frame_a.exists() or not first_frame_b.exists():
            print(f"❌ 프레임 파일을 찾을 수 없습니다: A={first_frame_a}, B={first_frame_b}")
            return False
        
        # 첫 프레임 로드
        sample_frame_a = cv2.imread(str(first_frame_a))
        sample_frame_b = cv2.imread(str(first_frame_b))
        if sample_frame_a is None or sample_frame_b is None:
            print("❌ 첫 프레임을 읽을 수 없습니다")
            return False
        
        # 개별 프레임 크기
        height_a, width_a = sample_frame_a.shape[:2]
        height_b, width_b = sample_frame_b.shape[:2]
        
        # 통합 프레임 크기 (좌우 배치 + 하단 대시보드)
        combined_width = width_a + width_b
        combined_height = max(height_a, height_b)
        dashboard_height = 120
        final_height = combined_height + dashboard_height
        
        print(f"📐 프레임 크기: A={width_a}x{height_a}, B={width_b}x{height_b}")
        print(f"📐 통합 크기: {combined_width}x{combined_height}")
        print(f"📐 최종 크기 (대시보드 포함): {combined_width}x{final_height}")
        
        # 🚀 높은 프레임 레이트로 부드러운 영상 생성
        frame_rate = 15  # 15fps로 부드럽게
        
        # 출력 디렉토리 확인 및 생성
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 다양한 코덱과 포맷을 시도하는 함수 (MP4 우선)
        def try_video_writer(path, width, height, fps):
            # 1. 기본 mp4v 코덱 (MP4) - 가장 호환성 좋음
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, path
            writer.release()
            
            # 2. MPEG-4 코덱 (MP4)
            fourcc = cv2.VideoWriter_fourcc(*'MP4V')
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, path
            writer.release()
            
            # 3. H.264 코덱 (MP4)
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, path
            writer.release()
            
            # 4. x264 코덱 (MP4)
            fourcc = cv2.VideoWriter_fourcc(*'x264')
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, path
            writer.release()
            
            # 5. avc1 코덱 (MP4) - H.264 대안
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, path
            writer.release()
            
            # 6. MJPG 코덱 (AVI) - 최후 수단
            avi_path = path.replace('.mp4', '.avi')
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            writer = cv2.VideoWriter(avi_path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, avi_path
            writer.release()
            
            # 7. XVID 코덱 (AVI) - 최후 수단
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            writer = cv2.VideoWriter(avi_path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, avi_path
            writer.release()
            
            return None, None
        
        # VideoWriter 초기화 시도 (최종 높이로 수정)
        print(f"🔄 VideoWriter 초기화 시도 중...")
        print(f"   출력 경로: {output_path}")
        print(f"   해상도: {combined_width}x{final_height}")
        print(f"   프레임레이트: {frame_rate}")
        
        out, final_output_path = try_video_writer(output_path, combined_width, final_height, frame_rate)
        
        if out is None:
            print(f"❌ 모든 코덱으로 VideoWriter 초기화 실패!")
            print(f"   시도한 코덱: mp4v, MP4V, H264, x264, avc1, MJPG, XVID")
            print(f"   해결 방안:")
            print(f"   1. 'sudo apt-get install ffmpeg' 실행")
            print(f"   2. 'pip install opencv-python opencv-contrib-python' 재설치")
            print(f"   3. 해상도를 짝수로 조정 (현재: {combined_width}x{final_height})")
            return False
        
        print(f"✅ VideoWriter 초기화 성공: {final_output_path}")
        output_path = final_output_path
        
        processed_frames = 0
        total_frames = len(continuous_frames)
        
        for frame_file_a, frame_file_b, frame_data, time_diff, is_real_data in continuous_frames:
            # 프레임 로드
            frame_a = cv2.imread(str(frame_file_a))
            frame_b = cv2.imread(str(frame_file_b))
            
            if frame_a is None or frame_b is None:
                print(f"⚠️ 프레임 로드 실패: A={frame_file_a.name}, B={frame_file_b.name}")
                continue
            
            # 프레임 크기 맞추기 (높이 기준)
            if frame_a.shape[0] != frame_b.shape[0]:
                target_height = max(frame_a.shape[0], frame_b.shape[0])
                if frame_a.shape[0] < target_height:
                    frame_a = cv2.resize(frame_a, (frame_a.shape[1], target_height))
                if frame_b.shape[0] < target_height:
                    frame_b = cv2.resize(frame_b, (frame_b.shape[1], target_height))
            
            # 🔧 모든 프레임에서 일관된 표시 (깜빡임 방지)
            if frame_data:
                # YOLO 감지 박스 그리기 - 각 카메라별로
                for detection in frame_data.get('detections', []):
                    if detection.get('camera') == 'A':
                        self.draw_detection_box(frame_a, detection)
                    elif detection.get('camera') == 'B':
                        self.draw_detection_box(frame_b, detection)
                
                # 위험도 정보 분리 표시
                self.draw_risk_info_only(frame_a, frame_data.get('risk_data'))  # A: 위험도 정보만
                
                # Frame 정보 생성
                frame_num = int(frame_file_a.stem.split('_')[-1])
                data_status = "REAL" if is_real_data else "INTERPOLATED"
                frame_info = f"Frame: {frame_num:06d} ({data_status})"
                if is_real_data and time_diff > 0:
                    frame_info += f", Sync: {time_diff:.3f}s"
                
                self.draw_minimap_and_info(frame_b, frame_data.get('risk_data'), frame_info)  # B: 미니맵+정보
            
            # 카메라 라벨 추가
            cv2.putText(frame_a, "Camera A", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)
            cv2.putText(frame_b, "Camera B", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)
            
            # 🎯 좌우 결합된 프레임 생성
            combined_frame = np.hstack((frame_a, frame_b))
            
            # 🎯 📈 하단 실시간 위험도 타임라인 그래프 추가
            frame_num = int(frame_file_a.stem.split('_')[-1])
            final_frame = self.draw_risk_timeline_graph(
                combined_frame, 
                frame_data.get('risk_data') if frame_data else None,
                frame_num,
                total_frames,
                risk_history  # 히스토리 전달
            )
            
            # 🎯 최종 프레임 추가
            out.write(final_frame)
            processed_frames += 1
        
        out.release()
        print(f"✅ 부드러운 데모 영상 완성: {output_path}")
        print(f"📊 총 {processed_frames}개 프레임 처리 ({frame_rate}fps)")
        print(f"🎯 하단 대시보드 포함된 완성 영상!")
        
        return True

    def create_demo_video(self, recording_path, log_file, output_path, delay_offset=0.0):
        """기존 방식 - 호환성 유지"""
        return self.create_smooth_demo_video(recording_path, log_file, output_path, delay_offset)

def find_latest_files():
    """가장 최신 Recording과 realtime_log 파일 자동 찾기"""
    from pathlib import Path
    import os
    
    # 현재 스크립트 위치 기준으로 절대 경로 계산
    script_dir = Path(__file__).parent
    
    # 최신 Recording 폴더 찾기
    sync_capture_dir = script_dir / '../data/sync_capture'
    recording_folders = list(sync_capture_dir.glob('Recording_*'))
    if not recording_folders:
        print(f"❌ Recording 폴더를 찾을 수 없습니다: {sync_capture_dir.resolve()}")
        print(f"   현재 스크립트 위치: {script_dir}")
        return None, None
    
    latest_recording = max(recording_folders, key=lambda p: p.stat().st_mtime)
    print(f"📁 최신 Recording: {latest_recording.name}")
    
    # 최신 realtime_log 파일 찾기
    log_dir = script_dir / '../data/realtime_results'  # 경로 수정
    log_files = list(log_dir.glob('realtime_log_*.json'))
    if not log_files:
        print(f"❌ realtime_log 파일을 찾을 수 없습니다: {log_dir.resolve()}")
        return None, None
    
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"📊 최신 Log: {latest_log.name}")
    
    return str(latest_recording), str(latest_log)

def main():
    demo = FixedRiskDemo()
    
    # 🚀 자동으로 최신 파일들 찾기
    recording_path, log_file = find_latest_files()
    if not recording_path or not log_file:
        print("❌ 필요한 파일들을 찾을 수 없습니다")
        return
    
    # 출력 파일명 생성 (타임스탬프 기반)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 🎯 최적의 offset_0.0 사용해서 최종 완성 영상 생성  
    output_path = f'./data/FINAL_risk_demo_{timestamp}.mp4'
    optimal_offset = 0.0  # 테스트 결과 최적값
    
    print(f"🎬 최종 위험도 데모 영상 생성 중... (최적 offset: {optimal_offset}초)")
    
    success = demo.create_demo_video(recording_path, log_file, output_path, optimal_offset)
    
    if success:
        print(f"\n🎉 최종 위험도 데모 영상 완성!")
        print(f"📹 파일: {output_path}")
        print(f"⚡ 최적 동기화 (offset: {optimal_offset}초) 적용")
    else:
        print(f"❌ 데모 영상 생성 실패")

if __name__ == "__main__":
    main() 