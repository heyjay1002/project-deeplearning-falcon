#!/usr/bin/env python3
"""
실시간 BDS (조류 탐지 시스템) 서버 파이프라인

실시간 항공기 탐지, 삼각측량, 트래킹 및 위험도 계산을 수행하는 통합 서버입니다.
"""

import os
import gc
import time
import json
import logging
import threading
import queue
import sys
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import numpy as np
import cv2
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 로컬 모듈 임포트
import bds_config as cfg
from aviation_detector import AviationDetector
from bds_tcp_client import BDSTCPClient, RiskLevel
from byte_track import SessionTracker
from triangulate import (
    triangulate_objects_realtime,
    get_projection_matrix,
    load_camera_parameters
)
from route_based_risk_calculator import RouteBasedRiskCalculator

warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class RealTimePipeline:
    """실시간 BDS 파이프라인"""
    
    def __init__(self):
        """파이프라인을 초기화합니다."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.project_root = Path(__file__).parent.parent
        
        # --- 구성 요소 초기화 ---
        self.aviation_detector: Optional[AviationDetector] = None
        self.camera_params: List[Dict] = []
        self.projection_matrices: List[np.ndarray] = []
        self.tracker: Optional[SessionTracker] = None
        self.route_calculator: Optional[RouteBasedRiskCalculator] = None
        self.tcp_client: Optional[BDSTCPClient] = None
        
        # --- 실시간 처리를 위한 큐 ---
        self.frame_queue = queue.Queue(maxsize=cfg.MAX_QUEUE_SIZE)
        
        # --- 상태 관리 ---
        self.is_running = False
        self.frame_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_risk_level = RiskLevel.BR_LOW
        self.skip_counter = 0

        # --- 경로 할당 ---
        self.airplane_route_mapping: Dict[int, str] = {}
        self.route_assignment_cache: Dict[int, str] = {}
        
        # --- 위험도 레벨 안정화 (히스테리시스) ---
        self.last_risk_level = 'BR_LOW'
        self.risk_level_downgrade_counter = 0
        self.downgrade_threshold = 5  # 하향 조정에 필요한 연속 프레임 수

        # --- 성능 모니터링 ---
        self.processing_times = {
            'detection': [], 'triangulation': [], 'tracking': [],
            'risk_calculation': [], 'total': []
        }
        
        # --- 디버깅 ---
        self.airplane_positions_log: List[Dict] = []
        self.debug_output_dir = Path("data/debug")
        self.debug_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("실시간 BDS 파이프라인 초기화 완료.")
        self.logger.info(f"성능 최적화: 매 {cfg.FRAME_SKIP} 프레임마다 처리.")
        self.logger.info(f"디버그 모드: 항공기 위치를 {self.debug_output_dir}에 저장.")

    def initialize_models(self) -> bool:
        """모든 모델과 파라미터를 초기화합니다."""
        try:
            if not self._initialize_detector(): return False
            if not self._initialize_camera_params(): return False
            if not self._initialize_tracker(): return False
            self._initialize_route_calculator() # 선택 사항
            self._initialize_tcp_client() # 선택 사항
            return True
        except Exception as e:
            self.logger.exception(f"모델 초기화 실패: {e}")
            return False

    def _initialize_detector(self) -> bool:
        """항공 감지 시스템을 초기화합니다."""
        model_path = None if cfg.MODEL_PATH == 'auto' else cfg.MODEL_PATH
        self.aviation_detector = AviationDetector(
            model_path=model_path,
            confidence_threshold=cfg.CONFIDENCE_THRESHOLD
        )
        if self.aviation_detector.model is None:
            self.logger.error("항공 감지 시스템 초기화 실패.")
            return False
        self.logger.info("항공 감지 시스템 초기화 성공.")
        return True

    def _initialize_camera_params(self) -> bool:
        """카메라 파라미터와 투영 행렬을 로드합니다."""
        sync_capture_dir = self.project_root / "data/sync_capture"
        if not sync_capture_dir.exists():
            self.logger.error(f"sync_capture 디렉토리를 찾을 수 없습니다: {sync_capture_dir}")
            return False

        latest_folder = max(sync_capture_dir.glob("Recording_*"), 
                              key=lambda p: p.stat().st_mtime, default=None)
        if not latest_folder:
            self.logger.error("sync_capture에서 'Recording_*' 폴더를 찾을 수 없습니다.")
            return False

        available_cameras = []
        camera_patterns = ["Camera_{}", "Fixed_Camera_{}"]
        for letter in cfg.CAMERA_LETTERS:
            camera_found = False
            for pattern in camera_patterns:
                params_path = latest_folder / f"{pattern.format(letter)}_parameters.json"
                if params_path.exists():
                    try:
                        params = load_camera_parameters(params_path)
                        self.camera_params.append(params)
                        P = get_projection_matrix(params)
                        self.projection_matrices.append(P)
                        available_cameras.append(letter)
                        self.logger.info(f"{pattern.format(letter)}의 파라미터를 로드했습니다.")
                        camera_found = True
                        break
                    except Exception as e:
                        self.logger.warning(f"{pattern.format(letter)}의 파라미터 로드 실패: {e}")
            if not camera_found:
                self.logger.warning(f"Camera_{letter}의 파라미터 파일을 찾을 수 없습니다.")

        if len(available_cameras) < 2:
            self.logger.error(f"최소 2대의 카메라가 필요하지만 {len(available_cameras)}대만 찾았습니다.")
            return False
        
        cfg.CAMERA_COUNT = len(available_cameras)
        cfg.CAMERA_LETTERS = available_cameras
        self.logger.info(f"{len(self.camera_params)}대의 카메라 파라미터를 로드했습니다: {', '.join(available_cameras)}")
        return True

    def _initialize_tracker(self) -> bool:
        """세션 추적 시스템을 초기화합니다."""
        tracking_config = cfg.TRACKING_CONFIG
        self.tracker = SessionTracker(
            position_jump_threshold=tracking_config['position_jump_threshold'],
            jump_duration_threshold=tracking_config['jump_duration_threshold'],
            min_session_length=tracking_config.get('min_episode_length', 10)
        )
        self.logger.info("세션 추적 시스템 초기화 완료.")
        self.logger.info(f"  - 모드: {cfg.TRACKING_MODE}")
        self.logger.info(f"  - 위치 점프 임계값: {tracking_config['position_jump_threshold']}m")
        self.logger.info(f"  - 최소 세션 길이: {tracking_config.get('min_episode_length', 10)} 프레임")
        return True

    def _initialize_route_calculator(self):
        """경로 기반 위험도 계산기를 초기화합니다."""
        try:
            routes_dir = self.project_root / "data/routes"
            self.route_calculator = RouteBasedRiskCalculator(str(routes_dir))
            available_routes = self.route_calculator.get_available_routes()
            if available_routes:
                self.logger.info("경로 기반 위험도 계산기 초기화 완료.")
                self.logger.info(f"  - 로드된 경로: {', '.join(available_routes)}")
            else:
                self.logger.warning("경로 계산기: 경로 데이터를 찾을 수 없어 실시간 계산만 사용합니다.")
        except Exception as e:
            self.logger.warning(f"경로 계산기 초기화 실패: {e}. 실시간 계산만 사용합니다.")
            self.route_calculator = None

    def _initialize_tcp_client(self):
        """메인 서버와 통신할 TCP 클라이언트를 초기화합니다."""
        if cfg.ENABLE_TCP:
            self.tcp_client = BDSTCPClient(host=cfg.TCP_HOST, port=cfg.TCP_PORT)
            self.logger.info(f"TCP 클라이언트 초기화 완료 ({cfg.TCP_HOST}:{cfg.TCP_PORT}) ")

    def watch_unity_frames(self):
        """새로운 Unity 프레임을 감시하고 큐에 추가합니다."""
        sync_capture_dir = self.project_root / "data/sync_capture"
        if not sync_capture_dir.exists():
            self.logger.error(f"프레임 감시 불가: {sync_capture_dir} 에서 디렉토리를 찾을 수 없습니다.")
            return

        current_recording_dir = None
        last_processed = {}
        self.logger.info(f"Unity 프레임 감시 시작: {sync_capture_dir}")

        while self.is_running:
            try:
                recording_folders = list(sync_capture_dir.glob("Recording_*"))
                if not recording_folders:
                    time.sleep(2.0)
                    continue
                
                latest_recording = max(recording_folders, key=lambda p: p.stat().st_mtime)
                
                if latest_recording != current_recording_dir:
                    current_recording_dir = latest_recording
                    last_processed = {letter: None for letter in cfg.CAMERA_LETTERS}
                    self.logger.info(f"새로운 녹화 세션 감지: {latest_recording.name}")
                
                new_frames = {}
                all_cameras_ready = True
                for letter in cfg.CAMERA_LETTERS:
                    camera_patterns = [f"Camera_{letter}", f"Fixed_Camera_{letter}"]
                    camera_dir = next((d for d in [current_recording_dir / p for p in camera_patterns] if d.exists()), None)
                    
                    if camera_dir:
                        image_files = sorted(list(camera_dir.glob("*.jpg")) + list(camera_dir.glob("*.png")))
                        if image_files:
                            latest_file = image_files[-1]
                            if latest_file != last_processed.get(letter):
                                new_frames[letter] = latest_file
                                last_processed[letter] = latest_file
                            else:
                                all_cameras_ready = False
                        else: all_cameras_ready = False
                    else: all_cameras_ready = False
                
                if all_cameras_ready and new_frames and len(new_frames) >= 2:
                    frame_data = {
                        "timestamp": time.time(), "frame_id": self.frame_count,
                        "images": new_frames, "recording_session": current_recording_dir.name
                    }
                    try:
                        self.frame_queue.put(frame_data, timeout=0.1)
                        self.frame_count += 1
                        if self.frame_count % (cfg.FPS_TARGET * 5) == 0:
                            self.logger.info(f"{self.frame_count}개의 프레임을 {len(new_frames)}대의 카메라에서 처리했습니다.")
                    except queue.Full:
                        self.logger.warning("프레임 큐가 가득 찼습니다. 프레임을 건너뜁니다.")
                
                time.sleep(1.0 / cfg.FPS_TARGET)
            except Exception as e:
                self.logger.exception(f"프레임 감시 중 오류 발생: {e}")
                time.sleep(1.0)

    def process_frame(self, frame_data: Dict) -> Optional[Dict]:
        """큐에서 단일 프레임 데이터를 처리합니다."""
        start_time = time.time()
        frame_id = frame_data['frame_id']
        
        try:
            self.skip_counter += 1
            if self.skip_counter % cfg.FRAME_SKIP != 0:
                return None

            # 1단계: 객체 탐지
            detection_start = time.time()
            detections = self.detect_objects(frame_data['images'])
            detection_time = time.time() - detection_start
            if not detections: return None
            
            self.logger.info(f"--- 프레임 {frame_id} 처리 중 ---")

            # 2단계: 삼각측량
            triangulation_start = time.time()
            triangulated_points = triangulate_objects_realtime(
                detections=detections, projection_matrices=self.projection_matrices,
                camera_letters=cfg.CAMERA_LETTERS, frame_id=frame_id,
                distance_threshold=cfg.DISTANCE_THRESHOLD
            )
            triangulation_time = time.time() - triangulation_start
            if not triangulated_points: return None
            
            self.log_airplane_positions(frame_id, triangulated_points)

            # 3단계: 추적
            tracking_start = time.time()
            self.tracker.update(frame_id, triangulated_points)
            active_tracks = self.get_active_tracks_from_sessions()
            tracking_time = time.time() - tracking_start

            # 4단계: 위험도 계산
            risk_calculation_time = 0
            risk_data = None
            if cfg.ENABLE_RISK_CALCULATION:
                risk_start = time.time()
                risk_data = self.calculate_risk(active_tracks, frame_id)
                risk_calculation_time = time.time() - risk_start
            
            total_time = time.time() - start_time
            
            # --- 성능 로깅 ---
            self.processing_times['detection'].append(detection_time)
            self.processing_times['triangulation'].append(triangulation_time)
            self.processing_times['tracking'].append(tracking_time)
            self.processing_times['risk_calculation'].append(risk_calculation_time)
            self.processing_times['total'].append(total_time)
            
            result = {
                'frame_id': frame_id, 'timestamp': frame_data['timestamp'],
                'detections': detections, 'triangulated_points': triangulated_points,
                'active_tracks': [self.track_to_dict(t) for t in active_tracks],
                'risk_data': risk_data,
                'processing_times': {
                    'detection': detection_time, 'triangulation': triangulation_time,
                    'tracking': tracking_time, 'risk_calculation': risk_calculation_time,
                    'total': total_time
                }
            }
            
            if frame_id % 50 == 0: gc.collect()
            
            self.logger.info(f"--- 프레임 {frame_id} 처리 완료 ({total_time*1000:.1f}ms) ---")
            return result
            
        except Exception as e:
            self.logger.exception(f"프레임 {frame_id} 처리 중 오류 발생: {e}")
            return None

    def detect_objects(self, images: Dict[str, Path]) -> List[Dict]:
        """이미지 배치에서 객체를 탐지합니다."""
        try:
            return self.aviation_detector.detect_batch_images_realtime(images)
        except Exception as e:
            self.logger.exception(f"배치 객체 탐지 중 오류 발생: {e}")
            return []

    def estimate_airplane_route(self, airplane_track: Dict) -> Optional[str]:
        """항공기 위치를 기반으로 비행 경로를 추정합니다."""
        try:
            if not self.route_calculator: return None
            track_id = airplane_track.get('track_id')
            if not track_id: return None
            if track_id in self.route_assignment_cache: return self.route_assignment_cache[track_id]

            # 데모를 위해 강제로 Path_A에 할당
            self.route_assignment_cache[track_id] = "Path_A"
            self.airplane_route_mapping[track_id] = "Path_A"
            self.logger.info(f"항공기 {track_id}를 경로에 할당: Path_A (강제)")
            return "Path_A"
                
        except Exception as e:
            self.logger.exception(f"항공기 경로 추정 중 오류 발생: {e}")
            return "Path_A"

    def calculate_risk(self, active_tracks: List, frame_id: int) -> Optional[Dict]:
        """경로 및 실시간 동역학을 기반으로 하이브리드 위험도를 계산합니다."""
        try:
            airplane_track = next((t for t in active_tracks if t.get('class_name') == 'Airplane'), None)
            flock_track = next((t for t in active_tracks if t.get('class_name') == 'Flock'), None)

            if active_tracks:
                track_info = [f"{t.get('class_name', 'Unk')}({t.get('track_id', '?')})" for t in active_tracks]
                self.logger.debug(f"활성 트랙: {', '.join(track_info)}")

            if not airplane_track:
                self.logger.debug("항공기가 탐지되지 않았습니다. 위험도를 계산할 수 없습니다.")
                return None
            
            if not flock_track:
                self.logger.debug("새 떼가 탐지되지 않았습니다. 위험도는 LOW입니다.")
                return {'risk_level': 'BR_LOW', 'risk_score': 0.0, 'distance_type': "NoFlock"}
            
            airplane_pos = airplane_track['positions'][-1] if airplane_track['positions'] else None
            flock_pos = flock_track['positions'][-1] if flock_track['positions'] else None
            if not airplane_pos or not flock_pos: return None

            # --- 경로 기반 계산 ---
            route_distance, assigned_route, route_direction = None, None, None
            if self.route_calculator:
                assigned_route = self.estimate_airplane_route(airplane_track)
                if assigned_route:
                    flock_3d_pos = np.array([flock_pos[0], 50.0, flock_pos[1]])
                    route_distance = self.route_calculator.calculate_distance_to_route(assigned_route, flock_3d_pos)
                    _, _, closest_point = self.route_calculator.get_closest_point_on_route(assigned_route, flock_3d_pos)
                    if closest_point is not None:
                        route_direction = self.route_calculator.calculate_route_segment_direction(assigned_route, closest_point)
                    self.logger.debug(f"경로 기반 계산: 경로={assigned_route}, 거리={route_distance:.1f}m")

            # --- 실시간 동적 계산 ---
            direct_distance = self.calculate_3d_distance(airplane_pos, flock_pos)
            relative_speed = self.calculate_relative_speed(airplane_track, flock_track)
            ttc = self.calculate_realtime_ttc(airplane_track, flock_track)

            # --- 하이브리드 거리 ---
            if route_distance is not None and route_distance < float('inf'):
                hybrid_distance = 0.7 * route_distance + 0.3 * direct_distance
                distance_type = "Hybrid"
            else:
                hybrid_distance = direct_distance
                distance_type = "Direct"
            
            # --- 위험도 레벨 ---
            risk_score, risk_level = self.calculate_dynamic_risk_level(hybrid_distance, relative_speed, ttc)
            stable_risk_score, stable_risk_level = self.get_stable_risk_level(risk_score, risk_level)
            
            risk_result = {
                'frame': frame_id, 'direct_distance': direct_distance, 'route_distance': route_distance,
                'hybrid_distance': hybrid_distance, 'distance_type': distance_type, 'assigned_route': assigned_route,
                'relative_speed': relative_speed, 'ttc': ttc, 'risk_score': stable_risk_score,
                'risk_level': stable_risk_level, 'raw_risk_score': risk_score, 'raw_risk_level': risk_level,
                'airplane_position': airplane_pos, 'flock_position': flock_pos,
                'route_direction': route_direction.tolist() if route_direction is not None else None
            }
            
            self.logger.info(f"위험도: {stable_risk_level} (점수: {stable_risk_score:.1f}, 거리: {hybrid_distance:.1f}m, TTC: {ttc:.1f}s)")
            self.print_detailed_risk_calculation(risk_result)
            
            # --- TCP 전송 ---
            if self.tcp_client and cfg.ENABLE_TCP and stable_risk_level != self.current_risk_level:
                try:
                    message = {"type": "event", "event": "BR_CHANGED", "result": stable_risk_level}
                    self.tcp_client.send_message(message)
                    self.current_risk_level = stable_risk_level
                    self.logger.info(f"TCP를 통해 위험도 업데이트 전송: {stable_risk_level}")
                except Exception as e:
                    self.logger.error(f"TCP 전송 오류: {e}")
            
            return risk_result
            
        except Exception as e:
            self.logger.exception(f"위험도 계산 중 오류 발생: {e}")
            return None

    def calculate_relative_speed(self, airplane_track: Dict, flock_track: Dict) -> float:
        """항공기와 새 떼 간의 상대 속도를 계산합니다."""
        try:
            airplane_vel = airplane_track.get('velocities', [])[-1]
            flock_vel = flock_track.get('velocities', [])[-1]
            airplane_pos = airplane_track['positions'][-1]
            flock_pos = flock_track['positions'][-1]
            
            dx, dz = airplane_pos[0] - flock_pos[0], airplane_pos[1] - flock_pos[1]
            distance = np.sqrt(dx**2 + dz**2)
            if distance < 1e-6: return 0.0
            
            unit_x, unit_z = dx / distance, dz / distance
            rel_vx, rel_vz = airplane_vel[0] - flock_vel[0], airplane_vel[1] - flock_vel[1]
            
            return rel_vx * unit_x + rel_vz * unit_z
        except (IndexError, TypeError) as e:
            self.logger.debug(f"상대 속도를 계산할 수 없습니다: {e}")
            return 0.0

    def calculate_realtime_ttc(self, airplane_track: Dict, flock_track: Dict) -> float:
        """충돌 시간(TTC)을 계산합니다."""
        try:
            airplane_pos = airplane_track['positions'][-1]
            flock_pos = flock_track['positions'][-1]
            airplane_vel = airplane_track.get('velocities', [])[-1]
            flock_vel = flock_track.get('velocities', [])[-1]

            dx, dz = airplane_pos[0] - flock_pos[0], airplane_pos[1] - flock_pos[1]
            current_distance = np.sqrt(dx**2 + dz**2)
            
            rel_vx, rel_vz = airplane_vel[0] - flock_vel[0], airplane_vel[1] - flock_vel[1]
            rel_speed_magnitude = np.sqrt(rel_vx**2 + rel_vz**2)

            if current_distance < 1e-6 or rel_speed_magnitude < 1e-6: return float('inf')
            
            unit_x, unit_z = dx / current_distance, dz / current_distance
            closing_speed = -(rel_vx * unit_x + rel_vz * unit_z)
            
            if closing_speed <= 0: return float('inf')
            
            ttc = current_distance / closing_speed
            return max(0.1, min(300.0, ttc))
        except (IndexError, TypeError) as e:
            self.logger.debug(f"TTC를 계산할 수 없습니다: {e}")
            return float('inf')

    def _calculate_risk_scores(self, distance: float, relative_speed: float, ttc: float) -> Dict[str, float]:
        """위험 평가를 위한 개별 점수 구성 요소를 계산합니다."""
        # 거리 점수 (가중치 40%)
        if distance <= 50: score_dist = 100
        elif distance <= 100: score_dist = 80 - (distance - 50) * 0.6
        elif distance <= 200: score_dist = 50 - (distance - 100) * 0.3
        else: score_dist = max(0, 20 - (distance - 200) * 0.05)
        
        # 속도 점수 (가중치 30%)
        if relative_speed <= 0: score_speed = 0
        elif relative_speed <= 10: score_speed = relative_speed * 3
        elif relative_speed <= 30: score_speed = 30 + (relative_speed - 10) * 2.5
        else: score_speed = min(100, 80 + (relative_speed - 30) * 1)
        
        # TTC 점수 (가중치 30%)
        if ttc == float('inf'): score_ttc = 0
        elif ttc <= 5: score_ttc = 100
        elif ttc <= 15: score_ttc = 100 - (ttc - 5) * 5
        elif ttc <= 30: score_ttc = 50 - (ttc - 15) * 2
        else: score_ttc = max(0, 20 - (ttc - 30) * 0.5)
            
        return {'distance': score_dist, 'speed': score_speed, 'ttc': score_ttc}

    def calculate_dynamic_risk_level(self, distance: float, relative_speed: float, ttc: float) -> Tuple[float, str]:
        """거리, 속도, TTC를 기반으로 동적 위험도 수준을 계산합니다."""
        # 하드코딩된 안전 임계값을 먼저 확인합니다.
        if distance < 50 or (ttc != float('inf') and ttc < 5): return 180.0, "BR_HIGH"
        if distance < 100 or (ttc != float('inf') and ttc < 12): return 120.0, "BR_MEDIUM"
        
        # 가중 점수를 계산합니다.
        scores = self._calculate_risk_scores(distance, relative_speed, ttc)
        risk_score = (scores['distance'] * 0.4 + scores['speed'] * 0.3 + scores['ttc'] * 0.3) * 2.0
        
        # 점수에서 위험도 수준을 결정합니다.
        if risk_score >= 80: risk_level = 'BR_HIGH'
        elif risk_score >= 60: risk_level = 'BR_MEDIUM'
        else: risk_level = 'BR_LOW'
        
        return risk_score, risk_level

    def print_detailed_risk_calculation(self, risk_data: Dict):
        """위험 계산에 대한 자세한 분석을 기록합니다."""
        try:
            self.logger.debug("--- 상세 위험도 분석 ---")
            # 거리 정보
            dist_info = f"직선: {risk_data['direct_distance']:.1f}m"
            if risk_data.get('route_distance') and risk_data['route_distance'] != float('inf'):
                dist_info += f", 경로: {risk_data['route_distance']:.1f}m ({risk_data['assigned_route']})"
            self.logger.debug(f"  거리 (하이브리드: {risk_data['hybrid_distance']:.1f}m): {dist_info}")

            # 점수
            scores = self._calculate_risk_scores(risk_data['hybrid_distance'], risk_data['relative_speed'], risk_data['ttc'])
            base_score = scores['distance'] * 0.4 + scores['speed'] * 0.3 + scores['ttc'] * 0.3
            self.logger.debug(f"  점수 (거리: {scores['distance']:.1f}, 속도: {scores['speed']:.1f}, TTC: {scores['ttc']:.1f})")
            self.logger.debug(f"  위험 점수: {base_score:.1f} * 2.0 = {risk_data['raw_risk_score']:.1f}")
            
            # 최종 레벨
            self.logger.debug(f"  계산된 레벨: {risk_data['raw_risk_level']}")
            if risk_data['risk_level'] != risk_data['raw_risk_level']:
                self.logger.debug(f"  안정화된 레벨: {risk_data['risk_level']} (이전: {self.last_risk_level})")
        except Exception as e:
            self.logger.warning(f"상세 위험도 계산을 출력할 수 없습니다: {e}")

    def get_stable_risk_level(self, new_risk_score: float, new_risk_level: str) -> Tuple[float, str]:
        """위험도 수준 깜박임을 방지하기 위해 히스테리시스를 적용합니다."""
        level_priority = {'BR_LOW': 0, 'BR_MEDIUM': 1, 'BR_HIGH': 2}
        prev_level, curr_level = self.last_risk_level, new_risk_level
        
        if level_priority[curr_level] > level_priority[prev_level]:
            self.last_risk_level = curr_level
            self.risk_level_downgrade_counter = 0
            self.logger.info(f"위험도 상향: {prev_level} -> {curr_level}")
            return new_risk_score, curr_level
        
        elif level_priority[curr_level] < level_priority[prev_level]:
            self.risk_level_downgrade_counter += 1
            if self.risk_level_downgrade_counter >= self.downgrade_threshold:
                self.last_risk_level = curr_level
                self.risk_level_downgrade_counter = 0
                self.logger.info(f"위험도 하향: {prev_level} -> {curr_level}")
                return new_risk_score, curr_level
            else:
                self.logger.debug(f"위험도 하향 대기: {prev_level} 유지 ({self.risk_level_downgrade_counter}/{self.downgrade_threshold})")
                prev_score = 120.0 if prev_level == 'BR_MEDIUM' else (180.0 if prev_level == 'BR_HIGH' else new_risk_score)
                return prev_score, prev_level
        else:
            self.risk_level_downgrade_counter = 0
            return new_risk_score, curr_level

    def calculate_3d_distance(self, airplane_pos: Tuple, flock_pos: Tuple) -> float:
        """고정된 고도 차이를 가정하여 3D 거리를 계산합니다."""
        try:
            dx = airplane_pos[0] - flock_pos[0]
            dz = airplane_pos[1] - flock_pos[1]
            horizontal_distance = np.sqrt(dx**2 + dz**2)
            altitude_diff = 50.0  # 가정된 고도 차이 (미터)
            return np.sqrt(horizontal_distance**2 + altitude_diff**2)
        except (TypeError, IndexError):
            return float('inf')

    def track_to_dict(self, track: Dict) -> Dict:
        """로깅을 위해 트랙 객체를 사전으로 변환합니다."""
        return {
            'track_id': track.get('track_id', 0),
            'class_name': track.get('class_name', 'Unknown'),
            'position': track['positions'][-1] if track.get('positions') else None,
            'velocity': track['velocities'][-1] if track.get('velocities') else None,
        }

    def get_active_tracks_from_sessions(self) -> List[Dict]:
        """현재 세션에서 활성 트랙 정보를 추출합니다."""
        active_tracks = []
        if self.tracker.in_session and self.tracker.current_session_data:
            s_data = self.tracker.current_session_data
            if s_data.get('airplane_positions'):
                active_tracks.append({
                    'track_id': 1, 'class_name': 'Airplane',
                    'positions': [(x, z) for _, x, z in s_data['airplane_positions']],
                    'velocities': [(vx, vz) for _, vx, vz in s_data.get('airplane_velocities', [])],
                })
            if s_data.get('flock_positions'):
                active_tracks.append({
                    'track_id': 2, 'class_name': 'Flock',
                    'positions': [(x, z) for _, x, z in s_data['flock_positions']],
                    'velocities': [(vx, vz) for _, vx, vz in s_data.get('flock_velocities', [])],
                })
        return active_tracks

    def process_frames_worker(self):
        """큐에서 프레임을 처리하는 워커 스레드입니다."""
        self.logger.info("프레임 처리 워커 시작.")
        while self.is_running:
            try:
                frame_data = self.frame_queue.get(timeout=1.0)
                self.process_frame(frame_data)
                
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    fps = self.fps_counter / (current_time - self.last_fps_time)
                    self.logger.info(f"처리 FPS: {fps:.1f}")
                    self.fps_counter = 0
                    self.last_fps_time = current_time
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.exception(f"프레임 처리 워커에서 오류 발생: {e}")

    def start(self):
        """파이프라인 실행을 시작합니다."""
        self.logger.info("실시간 BDS 파이프라인 시작 중...")
        if not self.initialize_models():
            self.logger.error("모델 초기화 오류로 파이프라인 시작 실패.")
            return False
        
        self.is_running = True
        
        if self.tcp_client:
            if self.tcp_client.start():
                self.logger.info("TCP 클라이언트 시작됨.")
            else:
                self.logger.warning("TCP 클라이언트 시작 실패, 재연결 시도.")
        
        threads = [
            threading.Thread(target=self.watch_unity_frames, daemon=True),
            threading.Thread(target=self.process_frames_worker, daemon=True),
        ]
        for thread in threads:
            thread.start()
        
        self.logger.info("모든 워커 스레드 시작됨. Unity 프레임 대기 중.")
        print("중지하려면 Ctrl+C를 누르세요")
        
        try:
            while True:
                time.sleep(5.0)
                tcp_status = ""
                if self.tcp_client:
                    status = self.tcp_client.get_status()
                    tcp_status = f", TCP: {'연결됨' if status['connected'] else '연결 끊김'}"
                self.logger.info(f"큐 상태 - 프레임: {self.frame_queue.qsize()}{tcp_status}")
                if self.frame_count > 0 and self.frame_count % 150 == 0:
                    self.print_performance_stats()
        except KeyboardInterrupt:
            self.logger.info("사용자 중단 요청 수신.")
            self.stop()
            return True

    def stop(self):
        """파이프라인 실행을 중지합니다."""
        self.logger.info("실시간 BDS 파이프라인 중지 중...")
        self.is_running = False
        
        if self.airplane_positions_log:
            self.logger.info("최종 디버그 데이터 저장 중...")
            self.save_airplane_debug_data()
        
        if self.tcp_client:
            self.tcp_client.stop()
            self.logger.info("TCP 클라이언트 중지됨.")
        
        time.sleep(2.0) # 스레드가 정리될 때까지 대기
        self.print_performance_stats()
        self.logger.info("파이프라인이 성공적으로 중지되었습니다.")

    def print_performance_stats(self):
        """성능 통계를 출력합니다."""
        if not self.processing_times['total']: return
        
        self.logger.info("--- 성능 통계 ---")
        self.logger.info(f"  처리된 프레임: {len(self.processing_times['total'])}")
        for stage, times in self.processing_times.items():
            if times:
                avg_time = np.mean(times) * 1000
                max_time = np.max(times) * 1000
                self.logger.info(f"  - {stage:<15}: 평균 {avg_time:6.1f}ms, 최대 {max_time:6.1f}ms")

    def log_airplane_positions(self, frame_id: int, triangulated_points: List[Dict]):
        """디버깅을 위해 항공기 위치를 기록합니다."""
        try:
            for point in triangulated_points:
                if point.get('class', '').lower() == 'airplane':
                    log_entry = {
                        'frame_id': frame_id, 'timestamp': time.time(),
                        'x': float(point['x']), 'y': float(point['y']), 'z': float(point['z']),
                        'confidence': point.get('confidence', 0.0)
                    }
                    self.airplane_positions_log.append(log_entry)
                    self.logger.debug(f"항공기 위치: 프레임 {frame_id} -> "
                                     f"Unity({point['x']:.1f}, {point['y']:.1f}, {point['z']:.1f})")
            
            if frame_id % 5 == 0 and self.airplane_positions_log:
                self.save_airplane_debug_data()
        except Exception as e:
            self.logger.warning(f"항공기 위치를 기록할 수 없습니다: {e}")

    def save_airplane_debug_data(self):
        """항공기 위치 데이터를 JSON 파일에 저장합니다."""
        try:
            if not self.airplane_positions_log: return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_output_dir / f"airplane_positions_{timestamp}.json"
            
            debug_data = {
                'session_start': datetime.now().isoformat(),
                'total_positions': len(self.airplane_positions_log),
                'frame_range': {
                    'start': self.airplane_positions_log[0]['frame_id'],
                    'end': self.airplane_positions_log[-1]['frame_id']
                },
                'coordinate_range': self.calculate_coordinate_range(),
                'positions': self.airplane_positions_log
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"디버그 데이터를 {debug_file.name}에 저장했습니다.")
            self.airplane_positions_log = []
        except Exception as e:
            self.logger.error(f"디버그 데이터 저장 실패: {e}")

    def calculate_coordinate_range(self) -> Dict:
        """기록된 좌표의 최소/최대 범위를 계산합니다."""
        if not self.airplane_positions_log: return {}
        
        x_coords = [p['x'] for p in self.airplane_positions_log]
        y_coords = [p['y'] for p in self.airplane_positions_log]
        z_coords = [p['z'] for p in self.airplane_positions_log]
        
        return {
            'x': {'min': min(x_coords), 'max': max(x_coords)},
            'y': {'min': min(y_coords), 'max': max(y_coords)},
            'z': {'min': min(z_coords), 'max': max(z_coords)}
        }

def main():
    """메인 실행 함수"""
    logging.info("BirdRiskSim 실시간 파이프라인을 시작합니다.")
    pipeline = RealTimePipeline()
    try:
        if pipeline.start():
            logging.info("파이프라인이 정상적으로 종료되었습니다.")
        else:
            logging.error("파이프라인 시작에 실패했습니다.")
    except Exception as e:
        logging.exception(f"파이프라인에서 처리되지 않은 오류가 발생했습니다: {e}")
        pipeline.stop()

if __name__ == "__main__":
    main()