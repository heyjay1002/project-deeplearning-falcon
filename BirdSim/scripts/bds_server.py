#!/usr/bin/env python3
"""
🎯 Real-time BDS (Bird Detection System) Server Pipeline

실시간 항공기 탐지, 삼각측량, 트래킹 및 위험도 계산을 수행하는 통합 서버
"""

import os
import gc
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
import cv2
import threading
import queue
import glob
import pandas as pd
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

# 📊 시각화를 위한 matplotlib (선택적 import)
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 🎯 항공 감지 모듈 import (YOLO 로직 통합)
from aviation_detector import AviationDetector
from bds_tcp_client import BDSTCPClient, RiskLevel

# 🔥 세션 트래킹 시스템 임포트 (Episode → Session 변경 반영)
from byte_track import SessionTracker

# 📐 삼각측량 모듈 임포트
from triangulate import (
    triangulate_objects_realtime,
    get_projection_matrix_simple,
    get_projection_matrix,
    load_camera_parameters
)

# 🛣️ 경로 기반 위험도 계산 모듈 임포트
from route_based_risk_calculator import RouteBasedRiskCalculator

warnings.filterwarnings('ignore')

class RealTimePipeline:
    """실시간 BDS 파이프라인"""
    
    def __init__(self, config_path: Optional[str] = None):
        """실시간 파이프라인 초기화"""
        
        # 프로젝트 루트 설정
        self.project_root = Path(__file__).parent.parent
        
        # 설정 로드
        self.config = self.load_config(config_path)
        
        # 기본 상태
        self.is_running = False
        self.frame_count = 0
        self.session_start_time = time.time()
        
        # 큐 초기화 (🚀 결과 저장 워커 제거)
        self.frame_queue = queue.Queue(maxsize=self.config['max_queue_size'])
        
        # 모델들
        self.aviation_detector = None
        self.projection_matrices = []
        
        # 트래킹 (🔥 Episode 대신 Session 사용)
        self.tracker = SessionTracker(
            position_jump_threshold=self.config.get('position_jump_threshold', 50.0),
            jump_duration_threshold=self.config.get('jump_duration_threshold', 5),
            min_session_length=self.config.get('min_session_length', 50)
        )
        
        # 경로 계산기
        self.route_calculator = None
        self.route_assignment_cache = {}  
        self.airplane_route_mapping = {}  
        
        # 성능 모니터링
        self.processing_times = {
            'detection': [],
            'triangulation': [],
            'tracking': [],
            'risk_calculation': [],
            'total': []
        }
        
        # 메모리 최적화를 위한 스킵 카운터 (제거)
        # self.skip_counter = 0
        # self.frame_skip = self.config.get('frame_skip', 2)  # 2프레임마다 1개 처리 (50% 감소)
        
        # 디버깅 출력 디렉토리
        self.debug_output_dir = Path('data/debug')
        self.debug_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 🐛 항공기 위치 로깅
        self.airplane_positions_log = []
        
        # 📊 위험도 데이터 로깅
        self.risk_log = []
        
        # 📊 실시간 세션 로그
        self.session_log = []
        
        # TCP 클라이언트 
        self.tcp_client = None
        self.current_risk_level = None
        
        # 위험도 안정화
        self.risk_history = []
        
        if self.config['enable_tcp']:
            try:
                from bds_tcp_client import BDSTCPClient
                self.tcp_client = BDSTCPClient(
                    host=self.config['tcp_host'],
                    port=self.config['tcp_port']
                )
                print(f"✅ TCP 클라이언트 초기화됨: {self.config['tcp_host']}:{self.config['tcp_port']}")
            except ImportError:
                print("⚠️ BDS TCP 클라이언트를 찾을 수 없습니다")
                self.tcp_client = None
            except Exception as e:
                print(f"❌ TCP 클라이언트 초기화 실패: {e}")
                self.tcp_client = None

        # 🎯 항공 감지 시스템 (통합 모듈 사용)
        self.camera_params = []
        
        # 🔄 위험도 레벨 안정화 (히스테리시스) - 보수적 안전 우선
        self.last_risk_level = 'BR_LOW'
        self.risk_level_downgrade_counter = 0
        self.downgrade_threshold = 100  # 하향 시 필요한 연속 프레임 수 (현재 미사용)
        
        # 🚨 위험도 상태 변화 필터링
        self.risk_level_history = []  # 최근 위험도 히스토리
        self.risk_history_size = 10   # 히스토리 크기
        self.risk_change_cooldown = 0  # 변화 후 쿨다운 카운터
        self.min_stable_frames = 5     # 안정적 상태 유지 필요 프레임 수
        self.last_sent_risk_level = 'BR_LOW'  # 마지막으로 전송된 위험도
        
        # FPS 카운터
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        print("🚀 실시간 BDS 파이프라인 초기화 완료")
        # print(f"⚡ 성능 최적화: 프레임 스킵 {self.frame_skip}프레임마다 1프레임 처리")  # 제거됨
        print(f"🐛 디버깅 모드: 항공기 위치 자동 저장 → {self.debug_output_dir}")
    
    def load_config(self, config_path: Optional[str]) -> Dict:
        """설정 로드 (환경변수 및 명령줄 인수 지원)"""
        default_config = {
            'unity_capture_dir': 'unity_capture',
            'camera_count': 2,
            'camera_letters': ['A', 'B'],
            'model_path': 'auto',  # 자동으로 최신 모델 탐지
            'confidence_threshold': 0.4,  # 🚀 NMS 최적화: 0.25 → 0.4
            'fps_target': 30,
            'max_queue_size': 10,
            'output_dir': 'data/realtime_results',
            'enable_visualization': True,
            'enable_risk_calculation': True,
            'distance_threshold': 100,  # 근접 무리 병합 임계값 (삼각측량용)
            'position_jump_threshold': 50.0,  # 위치 점프 임계값 (트래킹용)
            'jump_duration_threshold': 5,  # 점프 지속 임계값
            'min_session_length': 50,  # 최소 세션 길이
            'session_timeout': 30,  # 세션 타임아웃 (프레임)
            
            # 🌐 다중 환경 지원 TCP 설정
            'tcp_host': self._get_tcp_host(),  # 환경변수/인수 기반 동적 설정
            'tcp_port': self._get_tcp_port(),  # 환경변수/인수 기반 동적 설정
            'enable_tcp': True,  # TCP 통신 활성화
            
            # 🚀 성능 최적화 설정
            # 'frame_skip': 2,  # 프레임 스킵 (2프레임마다 1프레임 처리) - 제거됨
            
            # 🔥 새로운 트래킹 설정
            'tracking_mode': 'realtime',  # 'realtime' or 'episode'
            'tracking_config': {
                'position_jump_threshold': 50.0,  # 실시간용으로 더 민감하게
                'jump_duration_threshold': 3,     # 실시간용으로 더 짧게
                'min_episode_length': 10,         # 실시간용으로 더 짧게
                'enable_data_cleaning': True,     # 데이터 정제 활성화
                'realtime_mode': True             # 실시간 모드 플래그
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            default_config.update(user_config)
        
        return default_config
    
    def _get_tcp_host(self) -> str:
        """TCP 호스트 결정 - 사용자에게 직접 입력받기"""
        print("📡 TCP 서버 설정")
        print("   1. localhost (로컬 테스트)")
        print("   2. 192.168.0.12 (메인 서버)")
        print("   3. 직접 입력")
        
        while True:
            choice = input("선택하세요 (1/2/3): ").strip()
            
            if choice == '1':
                host = 'localhost'
                print(f"🌐 TCP 호스트 선택: {host}")
                return host
            elif choice == '2':
                host = '192.168.0.12'
                print(f"🌐 TCP 호스트 선택: {host}")
                return host
            elif choice == '3':
                host = input("TCP 호스트 주소를 입력하세요: ").strip()
                if host:
                    print(f"🌐 TCP 호스트 입력: {host}")
                    return host
                else:
                    print("❌ 유효한 호스트를 입력하세요.")
            else:
                print("❌ 1, 2, 또는 3을 선택하세요.")
    
    def _get_tcp_port(self) -> int:
        """TCP 포트 결정 - 사용자에게 직접 입력받기"""
        while True:
            port_input = input("TCP 포트를 입력하세요 (기본값: 5200): ").strip()
            
            if not port_input:  # 엔터만 누른 경우
                port = 5200
                print(f"🌐 TCP 포트 기본값 사용: {port}")
                return port
            
            try:
                port = int(port_input)
                if 1 <= port <= 65535:
                    print(f"🌐 TCP 포트 설정: {port}")
                    return port
                else:
                    print("❌ 포트는 1-65535 범위여야 합니다.")
            except ValueError:
                print("❌ 숫자를 입력하세요.")
    
    def initialize_models(self) -> bool:
        """모델 및 카메라 파라미터 초기화"""
        try:
            # 1. 🎯 항공 감지 시스템 초기화 (통합 모듈 사용)
            model_path = None if self.config['model_path'] == 'auto' else self.config['model_path']
            
            self.aviation_detector = AviationDetector(
                model_path=model_path,
                confidence_threshold=self.config['confidence_threshold']
            )
            
            if self.aviation_detector.model is None:
                print("❌ 항공 감지 시스템 초기화 실패")
                return False
            
            # 2. 카메라 파라미터 로드 (최신 캡처 폴더에서, 사용 가능한 카메라 자동 감지)
            sync_capture_dir = self.project_root / "data/sync_capture"
            if sync_capture_dir.exists():
                latest_folder = max(sync_capture_dir.glob("Recording_*"), 
                                  key=lambda p: p.stat().st_mtime, default=None)
                
                if latest_folder:
                    available_cameras = []
                    
                    # 가능한 모든 카메라 문자 확인 (Camera_* 및 Fixed_Camera_* 패턴 지원)
                    camera_patterns = ["Camera_{}", "Fixed_Camera_{}"]
                    
                    for letter in self.config['camera_letters']:
                        camera_found = False
                        
                        for pattern in camera_patterns:
                            params_path = latest_folder / f"{pattern.format(letter)}_parameters.json"
                            if params_path.exists():
                                try:
                                    # 🔧 삼각측량 모듈의 함수 사용
                                    params = load_camera_parameters(params_path)
                                    self.camera_params.append(params)
                                    
                                    # 🔧 삼각측량 모듈의 함수 사용 (Unity 원본 파라미터용)
                                    P = get_projection_matrix(params)
                                    self.projection_matrices.append(P)
                                    
                                    available_cameras.append(letter)
                                    print(f"  ✅ {pattern.format(letter)} 파라미터 로드 완료")
                                    camera_found = True
                                    break
                                except Exception as e:
                                    print(f"  ⚠️ {pattern.format(letter)} 파라미터 로드 실패: {e}")
                        
                        if not camera_found:
                            print(f"  ⚠️ Camera_{letter} 파라미터 파일 없음")
                    
                    if len(available_cameras) < 2:
                        print(f"❌ 최소 2개 이상의 카메라가 필요합니다. 현재 {len(available_cameras)}개 발견")
                        return False
                    
                    # 설정 업데이트
                    self.config['camera_count'] = len(available_cameras)
                    self.config['camera_letters'] = available_cameras
                    
                    print(f"✅ {len(self.camera_params)}개 카메라 파라미터 로드 완료")
                    print(f"📷 사용 카메라: {', '.join([f'Camera_{c}' for c in available_cameras])}")
                else:
                    print("❌ sync_capture 폴더에서 Recording_ 폴더를 찾을 수 없습니다")
                    return False
            else:
                print("❌ sync_capture 폴더를 찾을 수 없습니다")
                return False
            
            # 3. 🔥 세션 트래킹 시스템 초기화 (Episode → Session 변경 반영)
            self.tracker = SessionTracker(
                position_jump_threshold=self.config.get('position_jump_threshold', 50.0),
                jump_duration_threshold=self.config.get('jump_duration_threshold', 5),
                min_session_length=self.config.get('min_session_length', 50)
            )
            print(f"✅ 세션 트래킹 시스템 초기화 완료")
            print(f"   - 모드: {self.config.get('tracking_mode', 'realtime')}")
            print(f"   - 위치 점프 임계값: {self.config.get('position_jump_threshold', 50.0)}m")
            print(f"   - 최소 세션 길이: {self.config.get('min_session_length', 50)}프레임")
            
            # 4. 🛣️ 경로 기반 위험도 계산기 초기화
            try:
                # 프로젝트 루트 기준으로 절대 경로 사용
                routes_dir = self.project_root / "data/routes"
                self.route_calculator = RouteBasedRiskCalculator(str(routes_dir))
                available_routes = self.route_calculator.get_available_routes()
                if available_routes:
                    print(f"✅ 경로 기반 위험도 계산기 초기화 완료")
                    print(f"   - 로드된 경로: {', '.join(available_routes)}")
                    for route_name in available_routes:
                        info = self.route_calculator.get_route_info(route_name)
                        print(f"   - {route_name}: {info['total_route_points']}개 경로점")
                else:
                    print("⚠️ 경로 기반 위험도 계산기: 경로 데이터 없음 (실시간 계산만 사용)")
            except Exception as e:
                print(f"⚠️ 경로 기반 위험도 계산기 초기화 실패: {e}")
                print("   실시간 계산만 사용합니다.")
                self.route_calculator = None
            
            # 5. TCP 클라이언트는 __init__에서 이미 초기화됨
            if self.tcp_client:
                print(f"✅ TCP 클라이언트 사용 준비 완료 ({self.config['tcp_host']}:{self.config['tcp_port']})")
            
            return True
            
        except Exception as e:
            print(f"❌ 모델 초기화 실패: {e}")
            return False
    
    def watch_unity_frames(self):
        """Unity 프레임 감시 및 큐에 추가 (data/sync_capture 기반)"""
        sync_capture_dir = self.project_root / "data/sync_capture"
        
        if not sync_capture_dir.exists():
            print(f"❌ sync_capture 디렉토리를 찾을 수 없습니다: {sync_capture_dir}")
            return
        
        # 최신 Recording 폴더 찾기 및 감시
        current_recording_dir = None
        last_processed = {}
        
        print(f"👁️ Unity 프레임 감시 시작: {sync_capture_dir}")
        print(f"📁 Recording_* 폴더에서 실시간 프레임 감지 중...")
        
        while self.is_running:
            try:
                # 1. 최신 Recording 폴더 확인 (새로운 녹화 세션 감지)
                recording_folders = list(sync_capture_dir.glob("Recording_*"))
                if not recording_folders:
                    time.sleep(2.0)  # Recording 폴더가 생성될 때까지 대기
                    continue
                
                latest_recording = max(recording_folders, key=lambda p: p.stat().st_mtime)
                
                # 새로운 Recording 폴더 감지시 초기화
                if latest_recording != current_recording_dir:
                    current_recording_dir = latest_recording
                    last_processed = {letter: None for letter in self.config["camera_letters"]}
                    print(f"🔄 새로운 녹화 세션 감지: {latest_recording.name}")
                
                # 2. 현재 Recording 폴더에서 새로운 프레임 확인
                new_frames = {}
                all_cameras_ready = True
                
                for letter in self.config["camera_letters"]:
                    # Fixed_Camera_* 패턴 지원
                    camera_patterns = [f"Camera_{letter}", f"Fixed_Camera_{letter}"]
                    camera_dir = None
                    
                    for pattern in camera_patterns:
                        potential_dir = current_recording_dir / pattern
                        if potential_dir.exists():
                            camera_dir = potential_dir
                            break
                    
                    if camera_dir and camera_dir.exists():
                        # JPG 및 PNG 파일 모두 지원
                        image_files = sorted(list(camera_dir.glob("*.jpg")) + list(camera_dir.glob("*.png")))
                        
                        if image_files:
                            latest_file = image_files[-1]
                            
                            # 새로운 파일인지 확인
                            if latest_file != last_processed.get(letter):
                                new_frames[letter] = latest_file
                                last_processed[letter] = latest_file
                            else:
                                all_cameras_ready = False
                        else:
                            all_cameras_ready = False
                    else:
                        all_cameras_ready = False
                
                # 3. 모든 카메라에서 새 프레임이 준비되면 큐에 추가
                if all_cameras_ready and new_frames and len(new_frames) >= 2:  # 최소 2개 카메라
                    frame_data = {
                        "timestamp": time.time(),
                        "frame_id": self.frame_count,
                        "images": new_frames,
                        "recording_session": current_recording_dir.name
                    }
                    
                    try:
                        self.frame_queue.put(frame_data, timeout=0.1)
                        self.frame_count += 1
                        
                        # 진행 상황 로그 (5초마다)
                        if self.frame_count % (self.config["fps_target"] * 5) == 0:
                            print(f"📹 실시간 처리 중: {self.frame_count}프레임 ({len(new_frames)}개 카메라)")
                            
                    except queue.Full:
                        print("⚠️ 프레임 큐가 가득함 - 프레임 건너뜀")
                
                time.sleep(1.0 / self.config["fps_target"])  # FPS 제어
                
            except Exception as e:
                print(f"❌ 프레임 감시 오류: {e}")
                time.sleep(1.0)
    
    def process_frame(self, frame_data: Dict) -> Optional[Dict]:
        """단일 프레임 처리"""
        start_time = time.time()
        
        try:
            frame_id = frame_data['frame_id']
            images = frame_data['images']
            
            # 🚀 프레임 스킵 제거 - 모든 프레임 처리
            # (이전 코드 제거됨)
            
            # 1. YOLO 감지
            detection_start = time.time()
            detections = self.detect_objects(images)
            detection_time = time.time() - detection_start
            
            if not detections:
                return None
            
            # 실제 처리할 내용이 있을 때만 구분자 출력
            print(f"{'='*50}")
            print(f"📹 프레임 {frame_id} 처리 중")
            print(f"{'='*50}")
            
            # 2. 🔧 삼각측량 (모듈 함수 사용)
            triangulation_start = time.time()
            triangulated_points = triangulate_objects_realtime(
                detections=detections,
                projection_matrices=self.projection_matrices,
                camera_letters=self.config['camera_letters'],
                frame_id=frame_id,
                distance_threshold=self.config['distance_threshold']
            )
            triangulation_time = time.time() - triangulation_start
            
            if not triangulated_points:
                return None
            
            # 🐛 디버깅: 항공기 위치 로깅
            self.log_airplane_positions(frame_id, triangulated_points)
            
            # 3. 🔥 세션 트래킹 업데이트 (Episode → Session 변경 반영)
            tracking_start = time.time()
            self.tracker.update(frame_id, triangulated_points)
            
            # 현재 활성 트랙 가져오기 (세션에서 변환)
            active_tracks = self.get_active_tracks_from_sessions()
            tracking_time = time.time() - tracking_start
            
            # 4. 위험도 계산 (선택사항)
            risk_calculation_time = 0
            risk_data = None
            if self.config['enable_risk_calculation']:
                risk_start = time.time()
                risk_data = self.calculate_risk(active_tracks, frame_id)
                risk_calculation_time = time.time() - risk_start
                
                # 위험도 계산은 calculate_risk에서 출력하므로 여기서는 생략
            
            total_time = time.time() - start_time
            
            # 성능 모니터링
            self.processing_times['detection'].append(detection_time)
            self.processing_times['triangulation'].append(triangulation_time)
            self.processing_times['tracking'].append(tracking_time)
            self.processing_times['risk_calculation'].append(risk_calculation_time)
            self.processing_times['total'].append(total_time)
            
            # 결과 구성
            result = {
                'frame_id': frame_id,
                'timestamp': frame_data['timestamp'],
                'detections': detections,
                'triangulated_points': triangulated_points,
                'active_tracks': [self.track_to_dict(track) for track in active_tracks],
                'risk_data': risk_data,
                'processing_times': {
                    'detection': detection_time,
                    'triangulation': triangulation_time,
                    'tracking': tracking_time,
                    'risk_calculation': risk_calculation_time,
                    'total': total_time
                }
            }
            
            # 🚀 메모리 관리 최적화: 주기적 가비지 컬렉션
            if frame_id % 50 == 0:  # 50프레임마다 메모리 정리
                gc.collect()
            
            # 프레임 처리 완료 구분자
            print(f"{'='*50}")
            print(f"✅ 프레임 {frame_id} 처리 완료 ({total_time*1000:.1f}ms)")
            print(f"{'='*50}")
            
            # 📊 세션 로그에 결과 추가
            self.session_log.append(result)
            
            return result
            
        except Exception as e:
            print(f"❌ 프레임 {frame_data.get('frame_id', '?')} 처리 오류: {e}")
            return None
    
    def detect_objects(self, images: Dict[str, Path]) -> List[Dict]:
        """🎯 항공 객체 감지 (배치 처리 최적화)"""
        try:
            # 🚀 배치 처리로 모든 카메라 이미지를 한 번에 처리
            detections = self.aviation_detector.detect_batch_images_realtime(images)
            return detections
                        
        except Exception as e:
            print(f"❌ 배치 객체 감지 오류: {e}")
            return []
    
    def estimate_airplane_route(self, airplane_track: Dict) -> Optional[str]:
        """
        🛣️ 항공기 위치 기반 경로 추정
        
        Args:
            airplane_track: 항공기 트랙 정보
            
        Returns:
            추정된 경로명 또는 None
        """
        try:
            if not self.route_calculator:
                return "Path_A"  # 기본값
                
            track_id = airplane_track.get('track_id')
            if not track_id:
                return "Path_A"
            
            # 캐시에서 확인 (성능 최적화)
            if track_id in self.route_assignment_cache:
                return self.route_assignment_cache[track_id]
            
            # 현재는 모든 항공기를 Path_A로 할당 (추후 확장 가능)
            self.route_assignment_cache[track_id] = "Path_A"
            self.airplane_route_mapping[track_id] = "Path_A"
            
            return "Path_A"
                
        except Exception as e:
            print(f"❌ 항공기 경로 추정 오류: {e}")
            return "Path_A"  # 오류가 나도 Path_A 반환

    
    def send_risk_level_if_changed(self, new_risk_level: str):
        """🚨 위험도 레벨 필터링 및 TCP 전송 (급격한 변화 방지)"""
        
        # 히스토리에 현재 위험도 추가
        self.risk_level_history.append(new_risk_level)
        if len(self.risk_level_history) > self.risk_history_size:
            self.risk_level_history.pop(0)
        
        # 쿨다운 감소
        if self.risk_change_cooldown > 0:
            self.risk_change_cooldown -= 1
        
        # 필터링된 위험도 계산
        filtered_risk_level = self._get_filtered_risk_level()
        
        # TCP 전송 (변화가 있고 쿨다운이 끝났을 때만)
        if self.tcp_client and self.config['enable_tcp']:
            try:
                if filtered_risk_level != self.last_sent_risk_level and self.risk_change_cooldown == 0:
                    # 급격한 변화 체크
                    if self._is_valid_risk_transition(self.last_sent_risk_level, filtered_risk_level):
                        # RiskLevel enum으로 변환
                        from bds_tcp_client import RiskLevel
                        risk_level_enum = RiskLevel(filtered_risk_level)
                        
                        # BDS TCP 클라이언트의 올바른 메소드 사용
                        self.tcp_client.send_risk_update(risk_level_enum)
                        self.last_sent_risk_level = filtered_risk_level
                        self.current_risk_level = filtered_risk_level
                        
                        # 쿨다운 설정 (상태 변화 후 안정화 시간)
                        self.risk_change_cooldown = self.min_stable_frames
                        
                        print(f"📡 위험도 전송: {filtered_risk_level} (필터링됨)")
                    else:
                        print(f"⚠️ 급격한 위험도 변화 차단: {self.last_sent_risk_level} → {filtered_risk_level}")
                        
            except Exception as e:
                print(f"❌ TCP 전송 오류: {e}")
    
    def _get_filtered_risk_level(self) -> str:
        """히스토리 기반 필터링된 위험도 반환"""
        if len(self.risk_level_history) < self.min_stable_frames:
            return self.last_sent_risk_level  # 충분한 데이터 없으면 이전 값 유지
        
        # 최근 N개 프레임의 위험도 분석
        recent_levels = self.risk_level_history[-self.min_stable_frames:]
        
        # 가장 빈번한 위험도 계산
        level_counts = {}
        for level in recent_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # 가장 많이 나타난 위험도
        most_common_level = max(level_counts.items(), key=lambda x: x[1])[0]
        
        # 안정성 체크: 최근 프레임들이 충분히 일관성 있는지 확인
        consistency_ratio = level_counts[most_common_level] / len(recent_levels)
        
        if consistency_ratio >= 0.6:  # 60% 이상 일치하면 안정적
            return most_common_level
        else:
            return self.last_sent_risk_level  # 불안정하면 이전 값 유지
    
    def _is_valid_risk_transition(self, from_level: str, to_level: str) -> bool:
        """위험도 전환이 유효한지 체크 (급격한 변화 방지)"""
        
        # 위험도 레벨 순서 정의
        risk_order = {'BR_LOW': 0, 'BR_MEDIUM': 1, 'BR_HIGH': 2}
        
        from_order = risk_order.get(from_level, 0)
        to_order = risk_order.get(to_level, 0)
        
        # 같은 레벨이면 항상 유효
        if from_order == to_order:
            return True
        
        # 점진적 변화만 허용 (한 단계씩)
        level_diff = abs(to_order - from_order)
        
        if level_diff <= 1:
            return True  # 한 단계 변화는 허용
        else:
            # LOW → HIGH 또는 HIGH → LOW 같은 급격한 변화는 차단
            print(f"🚫 급격한 위험도 변화 차단: {from_level} → {to_level} (단계 차이: {level_diff})")
            return False

    def calculate_risk(self, active_tracks: List, frame_id: int) -> Optional[Dict]:
        """🚀 하이브리드 위험도 계산 (경로 기반 + 실시간 동적 계산)"""
        try:
            # 활성 트랙에서 항공기와 새떼 찾기
            airplane_track = None
            flock_track = None
            
            for track in active_tracks:
                if track['class_name'] == 'Airplane':
                    airplane_track = track
                elif track['class_name'] == 'Flock':
                    flock_track = track
            
            # 🔥 추가 검증: 객체가 최근에 감지되었는지 확인
            if airplane_track:
                frames_since_airplane = airplane_track.get('frames_since_last_detection', 0)
                if frames_since_airplane > 0:
                    print(f"⚠️ 항공기가 {frames_since_airplane}프레임 전에 마지막 감지됨")
            
            if flock_track:
                frames_since_flock = flock_track.get('frames_since_last_detection', 0)
                if frames_since_flock > 0:
                    print(f"⚠️ 새떼가 {frames_since_flock}프레임 전에 마지막 감지됨")
            
            # 항공기가 없으면 위험도 LOW로 설정
            if not airplane_track:
                print("✅ 항공기 미감지 - 위험도 LOW로 설정")
                risk_result = {
                    'frame': frame_id,
                    'direct_distance': float('inf'),
                    'route_distance': float('inf'),
                    'hybrid_distance': float('inf'),
                    'distance_type': "항공기없음",
                    'assigned_route': None,
                    'relative_speed': 0.0,
                    'ttc': float('inf'),
                    'risk_level': 'BR_LOW',
                    'raw_risk_level': 'BR_LOW',
                    'airplane_position': None,
                    'flock_position': None,
                    'route_direction': None
                }
                
                # 📊 위험도 변화 로깅 (시각화용)
                self.log_risk_data(frame_id, risk_result)
                
                # 위험도 출력 (매번)
                print(f"📊 위험도: BR_LOW")
                
                # TCP 전송 (공통 함수로 처리)
                self.send_risk_level_if_changed('BR_LOW')
                
                return risk_result
            
            # 새떼가 없으면 위험도 LOW로 설정
            if not flock_track:
                print("✅ 새떼 미감지 - 위험도 LOW로 설정")
                risk_result = {
                    'frame': frame_id,
                    'direct_distance': float('inf'),
                    'route_distance': float('inf'),
                    'hybrid_distance': float('inf'),
                    'distance_type': "새떼없음",
                    'assigned_route': None,
                    'relative_speed': 0.0,
                    'ttc': float('inf'),
                    'risk_level': 'BR_LOW',
                    'raw_risk_level': 'BR_LOW',
                    'airplane_position': airplane_track['positions'][-1] if airplane_track['positions'] else [0, 0],
                    'flock_position': None,
                    'route_direction': None
                }
                
                # 위험도 출력 (매번)
                print(f"📊 위험도: BR_LOW")
                
                # 📊 위험도 변화 로깅 (시각화용)
                try:
                    self.log_risk_data(frame_id, risk_result)
                except Exception as log_e:
                    print(f"⚠️ 위험도 로깅 오류: {log_e}")
                
                # TCP 전송 (공통 함수로 처리)
                self.send_risk_level_if_changed('BR_LOW')
                
                return risk_result
            
            # 최신 위치 정보
            airplane_pos = airplane_track['positions'][-1] if airplane_track['positions'] else None
            flock_pos = flock_track['positions'][-1] if flock_track['positions'] else None
            
            if not airplane_pos or not flock_pos:
                print("❌ 위치 정보 부족 - 위험도 LOW로 설정")
                risk_result = {
                    'frame': frame_id,
                    'direct_distance': float('inf'),
                    'route_distance': float('inf'),
                    'hybrid_distance': float('inf'),
                    'distance_type': "위치정보없음",
                    'assigned_route': None,
                    'relative_speed': 0.0,
                    'ttc': float('inf'),
                    'risk_level': 'BR_LOW',
                    'raw_risk_level': 'BR_LOW',
                    'airplane_position': airplane_pos,
                    'flock_position': flock_pos,
                    'route_direction': None
                }
                
                # 📊 위험도 변화 로깅 (시각화용)
                self.log_risk_data(frame_id, risk_result)
                
                # 위험도 출력 (매번)
                print(f"📊 위험도: BR_LOW")
                
                # TCP 전송 (공통 함수로 처리)
                self.send_risk_level_if_changed('BR_LOW')
                
                return risk_result
            
            # ✅ 새떼 높이 체크 (땅속에 있으면 위험도 LOW)
            # 삼각측량된 새떼 위치에서 Y좌표 확인
            if hasattr(flock_track, 'current_3d_position'):
                flock_y = flock_track.current_3d_position[1]
                if flock_y < 0:  # 땅속에 있음
                    print(f"⚠️ 새떼가 지하에 위치 (Y: {flock_y:.1f}m) - 위험도 LOW로 설정")
                    risk_result = {
                        'frame': frame_id,
                        'direct_distance': float('inf'),
                        'route_distance': float('inf'),
                        'hybrid_distance': float('inf'),
                        'distance_type': "새떼지하위치",
                        'assigned_route': None,
                        'relative_speed': 0.0,
                        'ttc': float('inf'),
                        'risk_level': 'BR_LOW',
                        'raw_risk_level': 'BR_LOW',
                        'airplane_position': airplane_pos,
                        'flock_position': flock_pos,
                        'route_direction': None
                    }
                    
                    # 📊 위험도 변화 로깅 (시각화용)
                    self.log_risk_data(frame_id, risk_result)
                    
                    # 위험도 출력 (매번)
                    print(f"📊 위험도: BR_LOW (새떼 지하 위치)")
                    
                    # TCP 전송 (공통 함수로 처리)
                    self.send_risk_level_if_changed('BR_LOW')
                    
                    return risk_result
            
            # 🛣️ 1. 항공기 경로 추정 및 경로 기반 위험도 계산
            route_distance = None
            assigned_route = None
            route_direction = None
            
            if self.route_calculator:
                try:
                    # 1-1. 항공기 경로 추정
                    assigned_route = self.estimate_airplane_route(airplane_track)
                    
                    if assigned_route:
                        # 1-2. 할당된 경로와 새떼 간의 거리 계산
                        flock_3d_pos = np.array([flock_pos[0], 50.0, flock_pos[1]])
                        route_distance = self.route_calculator.calculate_distance_to_route(assigned_route, flock_3d_pos)
                        
                        print(f"🛣️ 경로 기반 계산: {assigned_route} 경로 사용 (거리: {route_distance:.1f}m)")
                    else:
                        print(f"⚠️ 항공기 경로 미할당 - 직선 거리만 사용")
                        
                except Exception as e:
                    print(f"⚠️ 경로 기반 계산 오류: {e}")
            else:
                # 경로 계산기가 없을 때는 기본값 사용
                assigned_route = "Path_A"
                print(f"🛣️ 경로: {assigned_route} (경로 계산기 없음)")
            
            # 🚀 2. 실시간 동적 계산
            # 2-1. 직선 거리 계산 (고도 차이 포함)
            direct_distance = self.calculate_3d_distance(airplane_pos, flock_pos)
            
            # 2-2. 상대속도 계산 (실제 트래킹 데이터 기반)
            relative_speed = self.calculate_relative_speed(airplane_track, flock_track)
            
            # 2-3. 실시간 TTC 계산
            ttc = self.calculate_realtime_ttc(airplane_track, flock_track)
            
            # 🎯 3. 새로운 방향성 기반 위험도 계산
            risk_level, calculation_info = self.calculate_condition_based_risk_level(
                direct_distance, route_distance, airplane_track, flock_track
            )
            
            # 계산 상세 정보 추출
            effective_distance = calculation_info.get('effective_distance', direct_distance)
            distance_type = calculation_info.get('distance_type', '직선거리_만')
            is_approaching = calculation_info.get('is_approaching', False)
            direction_text = calculation_info.get('direction_text', '알수없음')
            reason = calculation_info.get('reason', '계산완료')
            
            # 🔄 4. 위험도 레벨 안정화 (플리커링 방지)
            stable_risk_level = self.get_stable_risk_level(risk_level)
            
            # 📊 5. 결과 구성 (안정화된 값 + 새로운 정보 사용)
            risk_result = {
                'frame': frame_id,
                'direct_distance': direct_distance,
                'route_distance': route_distance,
                'hybrid_distance': effective_distance,  # 효과적 거리로 변경
                'effective_distance': effective_distance,  # 새로운 필드
                'distance_type': distance_type,
                'assigned_route': assigned_route,
                'relative_speed': relative_speed,
                'ttc': ttc,
                'is_approaching': is_approaching,  # 새로운 필드
                'direction_text': direction_text,  # 새로운 필드
                'reason': reason,  # 새로운 필드
                'risk_level': stable_risk_level,  # 안정화된 레벨
                'raw_risk_level': risk_level,     # 원본 레벨 (디버깅용)
                'airplane_position': airplane_pos,
                'flock_position': flock_pos,
                'route_direction': route_direction.tolist() if route_direction is not None else None
            }
            
            # 📊 위험도 변화 로깅 (시각화용)
            self.log_risk_data(frame_id, risk_result)
            
            # 위험도 간단 요약 (새로운 정보 포함)
            print(f"📊 위험도: {stable_risk_level}")
            print(f"   🎯 {direction_text}, {distance_type}: {effective_distance:.1f}m")
            print(f"   📋 판단근거: {reason}")
            if ttc != float('inf'):
                print(f"   ⏰ TTC: {ttc:.1f}초")
            
            # 🔍 새로운 방향성 기반 위험도 계산 상세 출력
            self.print_new_risk_calculation_details(
                calculation_info, risk_level, stable_risk_level
            )
            
            # TCP 클라이언트로 위험도 전송 (안정화된 레벨 사용, 공통 함수로 처리)
            self.send_risk_level_if_changed(stable_risk_level)
            
            return risk_result
            
        except Exception as e:
            print(f"❌ 위험도 계산 오류: {e} - 위험도 LOW로 설정")
            risk_result = {
                'frame': frame_id,
                'direct_distance': float('inf'),
                'route_distance': float('inf'),
                'hybrid_distance': float('inf'),
                'distance_type': "계산오류",
                'assigned_route': None,
                'relative_speed': 0.0,
                'ttc': float('inf'),
                'risk_level': 'BR_LOW',
                'raw_risk_level': 'BR_LOW',
                'airplane_position': None,
                'flock_position': None,
                'route_direction': None
            }
            
            # 📊 위험도 변화 로깅 (시각화용)
            self.log_risk_data(frame_id, risk_result)
            
            # 위험도 출력 (매번)
            print(f"📊 위험도: BR_LOW")
            
            # TCP 전송 (공통 함수로 처리)
            self.send_risk_level_if_changed('BR_LOW')
            
            return risk_result
    
    def calculate_relative_speed(self, airplane_track: Dict, flock_track: Dict) -> float:
        """
        항공기와 새떼 간 상대속도 계산
        
        Args:
            airplane_track: 항공기 트랙 정보
            flock_track: 새떼 트랙 정보
            
        Returns:
            상대속도 (m/s) - 양수: 접근, 음수: 멀어짐
        """
        try:
            # 최신 속도 정보 가져오기
            airplane_velocities = airplane_track.get('velocities', [])
            flock_velocities = flock_track.get('velocities', [])
            
            if not airplane_velocities or not flock_velocities:
                return 0.0
            
            # 최신 속도 벡터
            airplane_vel = airplane_velocities[-1]  # (vx, vz)
            flock_vel = flock_velocities[-1]       # (vx, vz)
            
            # 현재 위치
            airplane_pos = airplane_track['positions'][-1]  # (x, z)
            flock_pos = flock_track['positions'][-1]        # (x, z)
            
            # 위치 벡터 (새떼에서 항공기로)
            dx = airplane_pos[0] - flock_pos[0]
            dz = airplane_pos[1] - flock_pos[1]
            distance = np.sqrt(dx**2 + dz**2)
            
            if distance < 1e-6:  # 너무 가까우면 0 반환
                return 0.0
            
            # 정규화된 방향 벡터
            unit_x = dx / distance
            unit_z = dz / distance
            
            # 상대속도 벡터 (항공기 속도 - 새떼 속도)
            rel_vx = airplane_vel[0] - flock_vel[0]
            rel_vz = airplane_vel[1] - flock_vel[1]
            
            # 상대속도의 방향성 성분 (양수: 접근, 음수: 멀어짐)
            relative_speed = rel_vx * unit_x + rel_vz * unit_z
            
            return relative_speed
            
        except Exception as e:
            print(f"❌ 상대속도 계산 오류: {e}")
            return 0.0
    
    def calculate_realtime_ttc(self, airplane_track: Dict, flock_track: Dict) -> float:
        """
        🚀 실시간 충돌 시간 계산 (Time-to-Collision)
        
        Args:
            airplane_track: 항공기 트랙 정보
            flock_track: 새떼 트랙 정보
            
        Returns:
            예상 충돌 시간 (초) - 무한대면 충돌하지 않음
        """
        try:
            # 위치와 속도 정보 가져오기
            airplane_pos = airplane_track['positions'][-1]
            flock_pos = flock_track['positions'][-1]
            airplane_velocities = airplane_track.get('velocities', [])
            flock_velocities = flock_track.get('velocities', [])
            
            if not airplane_velocities or not flock_velocities:
                return float('inf')
            
            # 최신 속도 벡터
            airplane_vel = airplane_velocities[-1]  # (vx, vz)
            flock_vel = flock_velocities[-1]       # (vx, vz)
            
            # 현재 거리
            dx = airplane_pos[0] - flock_pos[0]
            dz = airplane_pos[1] - flock_pos[1]
            current_distance = np.sqrt(dx**2 + dz**2)
            
            # 상대속도 벡터 (항공기 - 새떼)
            rel_vx = airplane_vel[0] - flock_vel[0]
            rel_vz = airplane_vel[1] - flock_vel[1]
            rel_speed_magnitude = np.sqrt(rel_vx**2 + rel_vz**2)
            
            # 접근 방향인지 확인
            if current_distance < 1e-6 or rel_speed_magnitude < 1e-6:
                return float('inf')
            
            # 정규화된 방향 벡터 (새떼에서 항공기로)
            unit_x = dx / current_distance
            unit_z = dz / current_distance
            
            # 접근 속도 계산 (양수면 접근 중)
            closing_speed = -(rel_vx * unit_x + rel_vz * unit_z)
            
            if closing_speed <= 0:
                # 멀어지고 있거나 평행하게 움직임
                return float('inf')
            
            # TTC 계산
            ttc = current_distance / closing_speed
            
            # 합리적인 범위로 제한 (0.1초 ~ 300초)
            ttc = max(0.1, min(300.0, ttc))
            
            return ttc
            
        except Exception as e:
            print(f"❌ 실시간 TTC 계산 오류: {e}")
            return float('inf')
    
    def calculate_dynamic_risk_level(self, distance: float, relative_speed: float, ttc: float) -> Tuple[float, str]:
        """
        🎯 방향성 기반 동적 위험도 계산 (완전히 새로운 체계)
        - 점수 계산 제거: 조건 기반 판단으로 변경
        - 방향성 고려: 접근/멀어짐에 따른 다른 기준 적용
        - 거리 선택: 상황에 따른 효과적 거리 사용
        
        Args:
            distance: 하이브리드 거리 (현재는 사용하지 않음 - 호환성 유지)
            relative_speed: 상대속도 (방향성 판단용)
            ttc: 충돌 예상 시간 (현재는 사용하지 않음)
            
        Returns:
            (위험도 점수, 위험도 레벨)
        """
        try:
            # ⚠️ 주의: 이 함수는 호환성을 위해 유지되지만
            # 실제 계산은 calculate_condition_based_risk_level에서 수행됨
            
            # 단순한 거리 기반 계산 (임시)
            if distance < 30:
                return 150.0, "BR_HIGH"
            elif distance < 60:
                return 75.0, "BR_MEDIUM"
            else:
                return 25.0, "BR_LOW"
                
        except Exception as e:
            print(f"❌ 임시 위험도 계산 오류: {e}")
            return 0.0, 'BR_LOW'

    def is_approaching_target(self, airplane_track: Dict, flock_track: Dict) -> bool:
        """
        🧭 항공기가 새떼에게 접근 중인지 판단
        
        Args:
            airplane_track: 항공기 트랙 정보
            flock_track: 새떼 트랙 정보
            
        Returns:
            True: 접근 중, False: 멀어짐 또는 평행
        """
        try:
            # 현재 위치
            airplane_pos = airplane_track['positions'][-1]  # (x, z)
            flock_pos = flock_track['positions'][-1]        # (x, z)
            
            # 항공기 속도 벡터
            airplane_velocities = airplane_track.get('velocities', [])
            if not airplane_velocities:
                return False  # 속도 정보 없으면 멀어짐으로 간주
            
            airplane_vel = airplane_velocities[-1]  # (vx, vz)
            
            # 항공기에서 새떼로의 방향 벡터
            dx = flock_pos[0] - airplane_pos[0]
            dz = flock_pos[1] - airplane_pos[1]
            
            # 거리가 너무 가까우면 접근으로 간주
            distance = np.sqrt(dx**2 + dz**2)
            if distance < 1e-6:
                return True
            
            # 속도와 방향의 내적 (코사인 유사도)
            dot_product = airplane_vel[0] * dx + airplane_vel[1] * dz
            
            # 양수면 접근, 음수면 멀어짐
            return dot_product > 0
            
        except Exception as e:
            print(f"❌ 방향성 판단 오류: {e}")
            return False  # 오류시 안전하게 멀어짐으로 간주

    def get_effective_distance(self, direct_distance: float, route_distance: float, 
                              is_approaching: bool) -> Tuple[float, str]:
        """
        🎯 상황에 따른 효과적 거리 선택
        
        Args:
            direct_distance: 직선 거리
            route_distance: 경로 거리  
            is_approaching: 접근 중 여부
            
        Returns:
            (효과적_거리, 사용된_거리_타입)
        """
        try:
            # 1. 접근 중이고 경로 거리가 유효한 경우
            if is_approaching and route_distance is not None and route_distance < float('inf'):
                # 직선거리와 경로거리 중 더 위험한(작은) 값 선택
                if route_distance < direct_distance:
                    return route_distance, "경로거리_우선"
                else:
                    return direct_distance, "직선거리_우선"
            
            # 2. 멀어지거나 경로 정보가 없는 경우
            else:
                return direct_distance, "직선거리_만"
                
        except Exception as e:
            print(f"❌ 효과적 거리 계산 오류: {e}")
            return direct_distance, "직선거리_오류대체"

    def calculate_condition_based_risk_level(self, direct_distance: float, route_distance: float, 
                                           airplane_track: Dict, flock_track: Dict) -> Tuple[float, str, Dict]:
        """
        🎯 방향성 기반 조건부 위험도 계산 (새로운 메인 함수)
        
        Args:
            direct_distance: 직선 거리
            route_distance: 경로 거리
            airplane_track: 항공기 트랙 정보
            flock_track: 새떼 트랙 정보
            
        Returns:
            (위험도_점수, 위험도_레벨, 계산_상세정보)
        """
        try:
            # 1. 방향성 판단
            is_approaching = self.is_approaching_target(airplane_track, flock_track)
            
            # 2. 효과적 거리 선택
            effective_distance, distance_type = self.get_effective_distance(
                direct_distance, route_distance, is_approaching
            )
            
            # 3. 조건 기반 위험도 계산
            direction_text = "접근중" if is_approaching else "멀어짐"
            
            # 조건 1: 즉시 위험 (20m 이하는 무조건 위험) - 현실 200m
            if effective_distance < 20:
                risk_level = "BR_HIGH"
                reason = f"즉시위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
            
            # 조건 2: 접근 중인 경우의 위험도
            elif is_approaching:
                if effective_distance < 50:  # 현실 500m
                    risk_level = "BR_HIGH"
                    reason = f"접근중_고위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
                elif effective_distance < 100:  # 현실 1000m
                    risk_level = "BR_MEDIUM"
                    reason = f"접근중_중위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
                else:
                    risk_level = "BR_LOW"
                    reason = f"접근중_저위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
            
            # 조건 3: 멀어지는 경우의 위험도 (더 관대한 기준)
            else:
                if effective_distance < 40:  # 현실 400m
                    risk_level = "BR_MEDIUM"
                    reason = f"멀어짐_중위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
                elif effective_distance < 80:  # 현실 800m
                    risk_level = "BR_LOW"
                    reason = f"멀어짐_저위험({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
                else:
                    risk_level = "BR_LOW"
                    reason = f"멀어짐_안전({effective_distance:.1f}m→{effective_distance*10:.0f}m)"
            
            # 4. 상세 정보 구성
            calculation_info = {
                'is_approaching': is_approaching,
                'direction_text': direction_text,
                'effective_distance': effective_distance,
                'distance_type': distance_type,
                'direct_distance': direct_distance,
                'route_distance': route_distance,
                'reason': reason
            }
            
            return risk_level, calculation_info
            
        except Exception as e:
            print(f"❌ 조건 기반 위험도 계산 오류: {e}")
            return 'BR_LOW', {'error': str(e)}
    
    def print_detailed_risk_calculation(self, distance: float, relative_speed: float, ttc: float, 
                                       risk_level: str, stable_risk_level: str,
                                       hybrid_distance: float, direct_distance: float, 
                                       route_distance: float, assigned_route: str) -> None:
        """
        🔍 위험도 계산 과정 상세 출력
        """
        try:
            print(f"🔍 위험도 계산 상세 분석:")
            
            # 1. 거리 정보
            print(f"   📏 거리 정보:")
            print(f"      • 직선 거리: {direct_distance:.1f}m")
            if route_distance and route_distance != float('inf'):
                print(f"      • 경로 거리: {route_distance:.1f}m ({assigned_route})")
                print(f"      • 하이브리드 거리: {hybrid_distance:.1f}m (직선30% + 경로70%)")
            else:
                print(f"      • 하이브리드 거리: {hybrid_distance:.1f}m (직선거리 사용)")
            
            # 2. 위험도 판단 (조건 기반)
            print(f"   🎯 위험도 판단:")
            print(f"      • 최종 레벨: {stable_risk_level}")
            if stable_risk_level != risk_level:
                print(f"      • 원본: {risk_level}")
                print(f"      • 안정화: {stable_risk_level}")
            
            # 3. 상대속도 및 TTC 정보 (참고용)
            speed_direction = "접근" if relative_speed > 0 else "멀어짐"
            print(f"   📊 참고 정보:")
            print(f"      • 상대속도: {relative_speed:.1f}m/s ({speed_direction})")
            if ttc != float('inf'):
                print(f"      • TTC: {ttc:.1f}초")
            else:
                print(f"      • TTC: 무한대 (충돌 안함)")
                
        except Exception as e:
            print(f"❌ 상세 분석 출력 오류: {e}")

    def get_stable_risk_level(self, new_risk_level: str) -> str:
        """
        🔄 진동 방지 안정화 로직 (보수적 안전 우선)
        - 상향(위험 증가): 2-3프레임 연속시 변경 (빠른 위험 대응)
        - 하향(위험 감소): 8-12프레임 연속시 변경 (매우 보수적 안전 판단)
        - 진동 방지: 최근 변경 이력 고려하여 역변경 제한
        
        Args:
            new_risk_level: 새로 계산된 위험도 레벨
            
        Returns:
            안정화된 위험도 레벨
        """
        try:
            # 위험도 등급 우선순위 (숫자가 높을수록 위험)
            level_priority = {'BR_LOW': 0, 'BR_MEDIUM': 1, 'BR_HIGH': 2}
            
            prev_level = self.last_risk_level
            curr_level = new_risk_level
            
            # 초기화
            if not hasattr(self, 'risk_level_upgrade_counter'):
                self.risk_level_upgrade_counter = 0
            if not hasattr(self, 'recent_changes'):
                self.recent_changes = []  # 최근 변경 이력
            
            # 🚫 진동 방지: 최근 5프레임 내에 역변경이 있었는지 체크
            current_time = time.time()
            self.recent_changes = [(t, prev_lvl, curr_lvl) for t, prev_lvl, curr_lvl in self.recent_changes 
                                 if current_time - t < 0.25]  # 0.25초(5프레임) 이내 이력만 유지
            
            # 역변경 체크 (A→B 후 B→A 방지)
            reverse_change_detected = False
            for change_time, old_prev, old_curr in self.recent_changes:
                if old_prev == curr_level and old_curr == prev_level:
                    reverse_change_detected = True
                    print(f"🚫 진동 방지: {prev_level}→{curr_level} 변경 차단 (최근 {old_prev}→{old_curr} 변경 있음)")
                    break
            
            # 1. 상향(위험 증가): 빠른 반응
            if level_priority[curr_level] > level_priority[prev_level] and not reverse_change_detected:
                self.risk_level_upgrade_counter += 1
                self.risk_level_downgrade_counter = 0  # 하향 카운터 리셋
                
                # 상향 임계값: 2-3프레임
                if level_priority[curr_level] - level_priority[prev_level] >= 2:
                    # 2단계 상승 (LOW→HIGH): 3프레임 필요
                    upgrade_threshold = 3
                else:
                    # 1단계 상승: 2프레임 필요  
                    upgrade_threshold = 2
                
                if self.risk_level_upgrade_counter >= upgrade_threshold:
                    self.last_risk_level = curr_level
                    self.risk_level_upgrade_counter = 0
                    self.recent_changes.append((current_time, prev_level, curr_level))
                    elapsed_seconds = upgrade_threshold / 20.0
                    print(f"⚠️ 위험도 상향: {prev_level} → {curr_level} ({elapsed_seconds:.2f}초 후 반영)")
                    return curr_level
                else:
                    remaining = upgrade_threshold - self.risk_level_upgrade_counter
                    print(f"🔄 위험도 상향 대기: {prev_level} 유지 ({remaining}프레임 더 필요)")
                    return prev_level
            
            # 2. 하향(위험 감소): 매우 신중한 반응 (보수적 안전 우선)
            elif level_priority[curr_level] < level_priority[prev_level] and not reverse_change_detected:
                self.risk_level_downgrade_counter += 1
                self.risk_level_upgrade_counter = 0  # 상향 카운터 리셋
                
                # 하향 임계값: 8-12프레임 (매우 보수적)
                if level_priority[prev_level] - level_priority[curr_level] >= 2:
                    # 2단계 하강 (HIGH→LOW): 12프레임 필요 (0.6초 대기)
                    downgrade_threshold = 12
                else:
                    # 1단계 하강: 8프레임 필요 (0.4초 대기)
                    downgrade_threshold = 8
                
                if self.risk_level_downgrade_counter >= downgrade_threshold:
                    self.last_risk_level = curr_level
                    self.risk_level_downgrade_counter = 0
                    self.recent_changes.append((current_time, prev_level, curr_level))
                    elapsed_seconds = downgrade_threshold / 20.0
                    print(f"✅ 위험도 하향: {prev_level} → {curr_level} ({elapsed_seconds:.2f}초 후 반영)")
                    return curr_level
                else:
                    remaining = downgrade_threshold - self.risk_level_downgrade_counter
                    print(f"🔄 위험도 하향 대기: {prev_level} 유지 ({remaining}프레임 더 필요)")
                    return prev_level
            
            # 3. 등급 유지 또는 진동 차단
            else:
                if reverse_change_detected:
                    # 진동 차단으로 인한 유지
                    pass
                else:
                    # 정상적인 등급 유지
                    self.risk_level_downgrade_counter = 0
                    self.risk_level_upgrade_counter = 0
                
                return curr_level if curr_level == prev_level else prev_level
                
        except Exception as e:
            print(f"❌ 위험도 안정화 오류: {e}")
            return new_risk_level
    
    def calculate_3d_distance(self, airplane_pos: Tuple[float, float], flock_pos: Tuple[float, float]) -> float:
        """
        🚀 3D 거리 계산 (고도 차이 포함)
        
        Args:
            airplane_pos: 항공기 위치 (x, z)
            flock_pos: 새떼 위치 (x, z)
            
        Returns:
            3D 거리 (미터)
        """
        try:
            # XZ 평면 거리
            dx = airplane_pos[0] - flock_pos[0]
            dz = airplane_pos[1] - flock_pos[1]
            horizontal_distance = np.sqrt(dx**2 + dz**2)
            
            # 고도 차이 (항공기는 보통 50m 높이에서 비행한다고 가정)
            altitude_diff = 50.0  # 미터
            
            # 3D 거리 계산
            distance_3d = np.sqrt(horizontal_distance**2 + altitude_diff**2)
            
            return distance_3d
            
        except Exception as e:
            print(f"❌ 3D 거리 계산 오류: {e}")
            return 100.0  # 기본값
    
    def track_to_dict(self, track) -> Dict:
        """트랙 객체를 딕셔너리로 변환"""
        return {
            'track_id': track.get('track_id', 0),
            'class_name': track.get('class_name', 'Unknown'),
            'current_position': track['positions'][-1] if track.get('positions') else None,
            'current_velocity': track['velocities'][-1] if track.get('velocities') else None,
            'session_id': track.get('session_id', 0),
            'frame_count': len(track.get('frames', []))
        }
    
    def get_active_tracks_from_sessions(self) -> List[Dict]:
        """현재 활성 세션에서 트랙 정보 추출 - 최근에 감지된 객체만 활성으로 처리"""
        active_tracks = []
        
        # 현재 진행중인 세션이 있다면
        if self.tracker.in_session and self.tracker.current_session_data:
            session_data = self.tracker.current_session_data
            current_frame = session_data.get('last_frame', 0)
            
            # 🔥 중요: 최근 5프레임 이내에 감지된 객체만 활성으로 간주
            activity_threshold = 5  # 프레임 수
            
            # 항공기 트랙 - 최근에 감지된 경우만
            if session_data.get('airplane_positions'):
                # 가장 최근 항공기 위치의 프레임 번호 확인
                last_airplane_frame = session_data['airplane_positions'][-1][0]
                
                # 최근 activity_threshold 프레임 이내에 감지되었다면 활성
                if current_frame - last_airplane_frame <= activity_threshold:
                    airplane_track = {
                        'track_id': 1,
                        'class_name': 'Airplane',
                        'positions': [(x, z) for _, x, z in session_data['airplane_positions']],
                        'velocities': [(vx, vz) for _, vx, vz in session_data.get('airplane_velocities', [])],
                        'frames': [f for f, _, _ in session_data['airplane_positions']],
                        'session_id': self.tracker.current_session_id,
                        'last_update': last_airplane_frame,
                        'frames_since_last_detection': current_frame - last_airplane_frame
                    }
                    active_tracks.append(airplane_track)
                else:
                    print(f"🚫 항공기 비활성: {current_frame - last_airplane_frame}프레임 동안 미감지")
            
            # 새떼 트랙 - 최근에 감지된 경우만
            if session_data.get('flock_positions'):
                # 가장 최근 새떼 위치의 프레임 번호 확인
                last_flock_frame = session_data['flock_positions'][-1][0]
                
                # 최근 activity_threshold 프레임 이내에 감지되었다면 활성
                if current_frame - last_flock_frame <= activity_threshold:
                    flock_track = {
                        'track_id': 2,
                        'class_name': 'Flock',
                        'positions': [(x, z) for _, x, z in session_data['flock_positions']],
                        'velocities': [(vx, vz) for _, vx, vz in session_data.get('flock_velocities', [])],
                        'frames': [f for f, _, _ in session_data['flock_positions']],
                        'session_id': self.tracker.current_session_id,
                        'last_update': last_flock_frame,
                        'frames_since_last_detection': current_frame - last_flock_frame
                    }
                    active_tracks.append(flock_track)
                else:
                    print(f"🚫 새떼 비활성: {current_frame - last_flock_frame}프레임 동안 미감지")
        
        return active_tracks
    
    def process_frames_worker(self):
        """프레임 처리 워커 스레드"""
        print("🔄 프레임 처리 워커 시작")
        
        while self.is_running:
            try:
                # 큐에서 프레임 가져오기
                frame_data = self.frame_queue.get(timeout=1.0)
                
                # 프레임 처리
                result = self.process_frame(frame_data)
                
                # FPS 계산
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    fps = self.fps_counter / (current_time - self.last_fps_time)
                    print(f"📊 처리 FPS: {fps:.1f}")
                    self.fps_counter = 0
                    self.last_fps_time = current_time
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 프레임 처리 워커 오류: {e}")
    
    def start(self):
        """파이프라인 시작"""
        print("🚀 실시간 BDS 파이프라인 시작...")
        
        # 모델 초기화
        if not self.initialize_models():
            print("❌ 모델 초기화 실패")
            return False
        
        self.is_running = True
        
        # TCP 클라이언트 시작
        if self.tcp_client:
            if self.tcp_client.start():
                print("✅ TCP 클라이언트 시작됨")
            else:
                print("⚠️ TCP 클라이언트 시작 실패 (재연결 시도 중)")
        
        # 워커 스레드 시작 (🚀 저장 워커 제거로 성능 최적화)
        threads = [
            threading.Thread(target=self.watch_unity_frames, daemon=True),
            threading.Thread(target=self.process_frames_worker, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
        
        print("✅ 모든 워커 스레드 시작됨")
        print("📡 Unity 프레임 대기 중...")
        print("Press Ctrl+C to stop")
        
        try:
            # 메인 루프 (모니터링)
            while True:
                time.sleep(5.0)
                
                # 큐 상태 출력 (🚀 저장 제거로 결과 큐 모니터링 제거)
                frame_queue_size = self.frame_queue.qsize()
                
                # TCP 상태 확인
                tcp_status = ""
                if self.tcp_client:
                    status = self.tcp_client.get_status()
                    tcp_status = f", TCP: {'연결됨' if status['connected'] else '연결 안됨'}"
                
                print(f"📊 큐 상태 - 프레임: {frame_queue_size}{tcp_status}")  # 🚀 결과 큐 제거
                
                # 성능 통계 출력 (30초마다)
                if self.frame_count > 0 and self.frame_count % 150 == 0:
                    self.print_performance_stats()
                
        except KeyboardInterrupt:
            print("\n🛑 사용자 중단 요청")
            self.stop()
            return True
    
    def stop(self):
        """파이프라인 중지"""
        print("🛑 실시간 BDS 파이프라인 중지 중...")
        
        self.is_running = False
        
        # 🐛 프로그램 종료 시 마지막 디버깅 데이터 저장
        if self.airplane_positions_log:
            print("🐛 프로그램 종료 - 마지막 디버깅 데이터 저장 중...")
            self.save_airplane_debug_data()
        
        # 📊 실시간 로그 저장
        if hasattr(self, 'session_log') and self.session_log:
            print("📊 실시간 로그 저장 중...")
            self.save_realtime_log()
        
        # 📊 위험도 변화 시각화 및 저장
        if self.risk_log:
            print("📊 위험도 변화 시각화 및 저장 중...")
            self.visualize_risk_timeline()
        
        # TCP 클라이언트 중지
        if self.tcp_client:
            self.tcp_client.stop()
            print("✅ TCP 클라이언트 중지됨")
        
        # 잠시 대기하여 워커 스레드들이 정리되도록 함
        time.sleep(2.0)
        
        # 최종 성능 통계 출력
        self.print_performance_stats()
        
        print("✅ 파이프라인 중지 완료")
    
    def print_performance_stats(self):
        """성능 통계 출력"""
        if not self.processing_times['total']:
            return
        
        print("\n📊 성능 통계:")
        print(f"  🚀 최적화 적용:")
        print(f"    - 배치 처리       : 활성화 (다중 카메라 동시 처리)")
        print(f"    - GPU 메모리 최적화: 활성화")
        print(f"    - NMS 최적화      : confidence {self.config['confidence_threshold']}")
        print(f"    - 메모리 관리     : 50프레임마다 가비지 컬렉션")
        print(f"  처리된 프레임   : {len(self.processing_times.get('total', []))}개")
        for stage, times in self.processing_times.items():
            if times:
                avg_time = np.mean(times) * 1000  # ms로 변환
                max_time = np.max(times) * 1000
                print(f"  {stage:15}: 평균 {avg_time:6.1f}ms, 최대 {max_time:6.1f}ms")

    def log_airplane_positions(self, frame_id: int, triangulated_points: List[Dict]):
        """🐛 디버깅용: 항공기 위치 로깅"""
        try:
            for point in triangulated_points:
                if point.get('class', '').lower() == 'airplane':
                    log_entry = {
                        'frame_id': frame_id,
                        'timestamp': time.time(),
                        'x': float(point['x']),
                        'y': float(point['y']),
                        'z': float(point['z']),
                        'confidence': point.get('confidence', 0.0)
                    }
                    self.airplane_positions_log.append(log_entry)
                    
                    # 실시간 출력
                    print(f"🛩️ 항공기 위치: Frame {frame_id} → Unity({point['x']:.1f}, {point['y']:.1f}, {point['z']:.1f})")
            
            # 5프레임마다 파일 저장 (홀수 프레임에서도 저장됨)
            if frame_id % 5 == 0 and self.airplane_positions_log:
                self.save_airplane_debug_data()
                
        except Exception as e:
            print(f"❌ 항공기 위치 로깅 오류: {e}")
    
    def save_airplane_debug_data(self):
        """🐛 디버깅용: 항공기 위치 데이터 저장"""
        try:
            if not self.airplane_positions_log:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_output_dir / f"airplane_positions_{timestamp}.json"
            
            debug_data = {
                'session_start': datetime.now().isoformat(),
                'total_positions': len(self.airplane_positions_log),
                'frame_range': {
                    'start': self.airplane_positions_log[0]['frame_id'] if self.airplane_positions_log else 0,
                    'end': self.airplane_positions_log[-1]['frame_id'] if self.airplane_positions_log else 0
                },
                'coordinate_range': self.calculate_coordinate_range(),
                'positions': self.airplane_positions_log
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            print(f"🐛 디버깅 데이터 저장: {debug_file.name} ({len(self.airplane_positions_log)}개 위치)")
            
            # 기존 로그 초기화 (메모리 절약)
            self.airplane_positions_log = []
            
        except Exception as e:
            print(f"❌ 디버깅 데이터 저장 실패: {e}")
    
    def calculate_coordinate_range(self) -> Dict:
        """좌표 범위 계산"""
        if not self.airplane_positions_log:
            return {}
        
        x_coords = [p['x'] for p in self.airplane_positions_log]
        y_coords = [p['y'] for p in self.airplane_positions_log]
        z_coords = [p['z'] for p in self.airplane_positions_log]
        
        return {
            'x': {'min': min(x_coords), 'max': max(x_coords)},
            'y': {'min': min(y_coords), 'max': max(y_coords)},
            'z': {'min': min(z_coords), 'max': max(z_coords)}
        }
    
    def log_risk_data(self, frame_id: int, risk_result: Dict):
        """📊 위험도 데이터 로깅 (시각화용)"""
        try:
            # 위험도 레벨을 숫자로 변환 (시각화용)
            level_to_num = {'BR_LOW': 0, 'BR_MEDIUM': 1, 'BR_HIGH': 2}
            
            log_entry = {
                'frame_id': frame_id,
                'timestamp': time.time(),
                'elapsed_time': time.time() - self.session_start_time,
                'risk_level': risk_result['risk_level'],
                'risk_level_num': level_to_num.get(risk_result['risk_level'], 0),
                'direct_distance': risk_result['direct_distance'],
                'route_distance': risk_result.get('route_distance'),
                'hybrid_distance': risk_result['hybrid_distance'],
                'relative_speed': risk_result['relative_speed'],
                'ttc': risk_result['ttc'] if risk_result['ttc'] != float('inf') else None,
                'distance_type': risk_result['distance_type'],
                'assigned_route': risk_result['assigned_route']
            }
            
            self.risk_log.append(log_entry)
            
        except Exception as e:
            print(f"❌ 위험도 데이터 로깅 오류: {e}")
    
    def save_realtime_log(self):
        """📊 실시간 세션 로그를 JSON 파일로 저장"""
        try:
            if not hasattr(self, 'session_log') or not self.session_log:
                print("⚠️ 저장할 세션 로그가 없습니다")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = Path('data/realtime_results') / f"realtime_log_{timestamp}.json"
            
            # 디렉토리 생성
            log_file.parent.mkdir(parents=True, exist_ok=True)
            

            
            # JSON 직렬화 클래스 정의
            class NumpyEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
                        return int(obj)
                    elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, np.bool_):
                        return bool(obj)
                    return super().default(obj)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_log, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
            
            print(f"✅ 실시간 로그 저장: {log_file.name} ({len(self.session_log)}개 프레임)")
            
        except Exception as e:
            print(f"❌ 실시간 로그 저장 실패: {e}")
    
    def visualize_risk_timeline(self):
        """📊 위험도 변화 시각화 및 저장"""
        try:
            if not self.risk_log:
                print("⚠️ No risk data available, skipping visualization")
                return
            
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime, timedelta
            import numpy as np
            
            print(f"📊 Starting risk visualization... ({len(self.risk_log)} data points)")
            
            # 데이터 준비 및 무한대 값 필터링
            times = [entry['elapsed_time'] for entry in self.risk_log]
            risk_levels = [entry['risk_level_num'] for entry in self.risk_log]
            
            # 🔧 거리 데이터 필터링 (무한대 값 제거)
            raw_distances = [entry['hybrid_distance'] for entry in self.risk_log]
            distances = [d if d != float('inf') and np.isfinite(d) else 1000.0 for d in raw_distances]  # inf를 1000m로 대체
            
            # 직선 거리도 필터링
            raw_direct_distances = [entry['direct_distance'] for entry in self.risk_log]
            direct_distances = [d if d != float('inf') and np.isfinite(d) else 1000.0 for d in raw_direct_distances]
            
            relative_speeds = [entry['relative_speed'] for entry in self.risk_log]
            
            # TTC 데이터 필터링 (무한대와 None 제거)
            ttcs = []
            ttc_times = []
            for entry in self.risk_log:
                if entry['ttc'] is not None and entry['ttc'] != float('inf') and np.isfinite(entry['ttc']):
                    ttcs.append(entry['ttc'])
                    ttc_times.append(entry['elapsed_time'])
            
            # 그래프 스타일 설정
            plt.style.use('default')
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('BDS Real-time Risk Analysis Report', fontsize=16, fontweight='bold')
            
            # 색상 맵
            level_colors = {'BR_LOW': '#2ecc71', 'BR_MEDIUM': '#f39c12', 'BR_HIGH': '#e74c3c'}
            
            # 1. 위험도 레벨 타임라인
            ax1 = axes[0, 0]
            # 색상 배열을 데이터 길이에 맞춰 생성
            colors = [level_colors.get(entry['risk_level'], '#95a5a6') for entry in self.risk_log[:len(times)]]
            ax1.scatter(times, risk_levels, c=colors, alpha=0.7, s=20)
            ax1.plot(times, risk_levels, color='gray', alpha=0.3, linewidth=1)
            ax1.set_title('Risk Level Timeline', fontweight='bold')
            ax1.set_xlabel('Elapsed Time (seconds)')
            ax1.set_ylabel('Risk Level')
            ax1.set_yticks([0, 1, 2])
            ax1.set_yticklabels(['LOW', 'MEDIUM', 'HIGH'])
            ax1.grid(True, alpha=0.3)
            
            # 범례 추가
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=level_colors['BR_LOW'], label='LOW'),
                             Patch(facecolor=level_colors['BR_MEDIUM'], label='MEDIUM'),
                             Patch(facecolor=level_colors['BR_HIGH'], label='HIGH')]
            ax1.legend(handles=legend_elements, loc='upper left')
            
            # 2. 거리 분포 히스토그램 (무한대 값 제외)
            ax2 = axes[0, 1]
            # 유한한 거리 값만 사용
            finite_distances = [d for d in distances if d < 1000.0]  # 대체값 제외
            if finite_distances:
                ax2.hist(finite_distances, bins=20, alpha=0.7, color='#3498db', edgecolor='black')
                ax2.set_title('Distance Distribution (finite values only)', fontweight='bold')
                ax2.set_xlabel('Distance (meters)')
                ax2.set_ylabel('Frequency')
                ax2.grid(True, alpha=0.3)
                
                # 위험 거리 임계값 표시
                ax2.axvline(x=20, color='#e74c3c', linestyle='--', alpha=0.7, label='HIGH Threshold')
                ax2.axvline(x=50, color='#f39c12', linestyle='--', alpha=0.7, label='MEDIUM Threshold')
                ax2.axvline(x=100, color='#2ecc71', linestyle='--', alpha=0.7, label='LOW Threshold')
                ax2.legend()
            else:
                ax2.text(0.5, 0.5, 'No finite distance data', transform=ax2.transAxes, 
                        ha='center', va='center', fontsize=14)
                ax2.set_title('Distance Distribution', fontweight='bold')
            
            # 3. 거리 변화 (무한대 값 처리)
            ax3 = axes[1, 0]
            ax3.plot(times, distances, color='#9b59b6', linewidth=2, label='Hybrid Distance')
            
            # 직선 거리도 표시 (다르면)
            if any(abs(d - h) > 1 for d, h in zip(direct_distances, distances) if d < 1000.0 and h < 1000.0):
                ax3.plot(times, direct_distances, color='#34495e', linewidth=1, alpha=0.6, 
                        label='Direct Distance', linestyle='--')
            
            ax3.set_title('Distance Changes', fontweight='bold')
            ax3.set_xlabel('Elapsed Time (seconds)')
            ax3.set_ylabel('Distance (meters)')
            ax3.grid(True, alpha=0.3)
            ax3.legend()
            
            # Y축 범위 제한 (1000m 이하만 표시)
            ax3.set_ylim(0, min(1000, max(distances) * 1.1))
            
            # 위험 거리 임계값 표시
            ax3.axhline(y=50, color='#e74c3c', linestyle=':', alpha=0.7, label='Immediate Risk')
            ax3.axhline(y=100, color='#f39c12', linestyle=':', alpha=0.7, label='Caution Required')
            
            # 4. TTC 및 상대속도
            ax4 = axes[1, 1]
            if ttcs and ttc_times:
                # TTC는 왼쪽 y축 (유한한 값만)
                ax4_twin = ax4.twinx()
                line1 = ax4.plot(ttc_times, ttcs, color='#e74c3c', linewidth=2, label='TTC (seconds)')
                ax4.set_ylabel('TTC (seconds)', color='#e74c3c')
                ax4.tick_params(axis='y', labelcolor='#e74c3c')
                
                # 상대속도는 오른쪽 y축
                line2 = ax4_twin.plot(times, relative_speeds, color='#27ae60', linewidth=2, label='Relative Speed (m/s)')
                ax4_twin.set_ylabel('Relative Speed (m/s)', color='#27ae60')
                ax4_twin.tick_params(axis='y', labelcolor='#27ae60')
                
                # 범례 통합
                lines = line1 + line2
                labels = [l.get_label() for l in lines]
                ax4.legend(lines, labels, loc='upper left')
                
                # TTC 위험 임계값
                ax4.axhline(y=5, color='#e74c3c', linestyle=':', alpha=0.7)
                ax4.axhline(y=12, color='#f39c12', linestyle=':', alpha=0.7)
            else:
                ax4.plot(times, relative_speeds, color='#27ae60', linewidth=2)
                ax4.set_ylabel('Relative Speed (m/s)')
            
            ax4.set_title('Time-to-Collision (TTC) & Relative Speed', fontweight='bold')
            ax4.set_xlabel('Elapsed Time (seconds)')
            ax4.grid(True, alpha=0.3)
            
            # 레이아웃 조정
            plt.tight_layout()
            
            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            viz_file = self.debug_output_dir / f"risk_timeline_{timestamp}.png"
            plt.savefig(viz_file, dpi=300, bbox_inches='tight')
            
            # 통계 정보 추가
            stats_text = self.generate_risk_statistics()
            
            # 통계 텍스트 파일도 저장
            stats_file = self.debug_output_dir / f"risk_statistics_{timestamp}.txt"
            with open(stats_file, 'w', encoding='utf-8') as f:
                f.write(stats_text)
            
            print(f"✅ Risk visualization completed:")
            print(f"   📊 Chart: {viz_file.name}")
            print(f"   📋 Statistics: {stats_file.name}")
            
            # 메모리 정리
            plt.close(fig)
            
        except ImportError:
            print("⚠️ matplotlib not installed, skipping visualization")
            print("   Install with: pip install matplotlib")
        except Exception as e:
            print(f"❌ Risk visualization error: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
    
    def generate_risk_statistics(self) -> str:
        """📋 위험도 통계 생성"""
        try:
            import numpy as np
            
            if not self.risk_log:
                return "No risk data available"
            
            total_time = self.risk_log[-1]['elapsed_time']
            total_frames = len(self.risk_log)
            
            # 위험도 레벨별 시간 계산
            level_counts = {'BR_LOW': 0, 'BR_MEDIUM': 0, 'BR_HIGH': 0}
            for entry in self.risk_log:
                level_counts[entry['risk_level']] += 1
            
            # 거리 통계 (무한대 값 필터링)
            raw_distances = [entry['hybrid_distance'] for entry in self.risk_log]
            finite_distances = [d for d in raw_distances if d != float('inf') and np.isfinite(d)]
            
            if finite_distances:
                min_distance = min(finite_distances)
                max_distance = max(finite_distances)
                avg_distance = sum(finite_distances) / len(finite_distances)
            else:
                min_distance = max_distance = avg_distance = float('inf')
            
            # TTC 통계 (무한대와 None 값 필터링)
            ttcs = [entry['ttc'] for entry in self.risk_log 
                   if entry['ttc'] is not None and entry['ttc'] != float('inf') and np.isfinite(entry['ttc'])]
            min_ttc = min(ttcs) if ttcs else None
            avg_ttc = sum(ttcs) / len(ttcs) if ttcs else None
            
            # 무한대 처리된 통계 텍스트 생성
            if finite_distances:
                distance_stats = f"""Distance Statistics:
  Minimum Distance: {min_distance:.1f}m
  Maximum Distance: {max_distance:.1f}m
  Average Distance: {avg_distance:.1f}m
  Finite Distance Samples: {len(finite_distances)}/{len(raw_distances)}"""
            else:
                distance_stats = f"""Distance Statistics:
  No finite distance data available
  All distances were infinite (objects not detected together)"""
            
            if ttcs:
                ttc_stats = f"""Time-to-Collision (TTC) Statistics:
  Minimum TTC: {min_ttc:.1f}s (most dangerous moment)
  Average TTC: {avg_ttc:.1f}s
  TTC Samples: {len(ttcs)}/{len(self.risk_log)}"""
            else:
                ttc_stats = f"""Time-to-Collision (TTC) Statistics:
  No TTC data (no collision risk detected)"""
            
            stats = f"""
BDS Real-time Risk Analysis Report
{'='*50}

Session Information:
  Total Runtime: {total_time:.1f}s ({total_time/60:.1f}min)
  Processed Frames: {total_frames}
  Average FPS: {total_frames/total_time:.1f}

Risk Level Distribution:
  LOW: {level_counts['BR_LOW']} frames ({level_counts['BR_LOW']/total_frames*100:.1f}%)
  MEDIUM: {level_counts['BR_MEDIUM']} frames ({level_counts['BR_MEDIUM']/total_frames*100:.1f}%)
  HIGH: {level_counts['BR_HIGH']} frames ({level_counts['BR_HIGH']/total_frames*100:.1f}%)

{distance_stats}

{ttc_stats}
"""
            
            return stats
            
        except Exception as e:
            return f"Statistics generation error: {e}"

    def print_new_risk_calculation_details(self, calculation_info: Dict, 
                                          raw_risk_level: str, stable_risk_level: str) -> None:
        """
        🔍 새로운 방향성 기반 위험도 계산 상세 출력
        
        Args:
            calculation_info: 계산 상세 정보
            raw_risk_level: 원본 위험도 레벨
            stable_risk_level: 안정화된 위험도 레벨
        """
        try:
            print(f"🔍 방향성 기반 위험도 계산 상세:")
            
            # 1. 방향성 정보
            is_approaching = calculation_info.get('is_approaching', False)
            direction_text = calculation_info.get('direction_text', '알수없음')
            print(f"   🧭 방향성: {direction_text} ({'접근' if is_approaching else '멀어짐'})")
            
            # 2. 거리 정보
            direct_distance = calculation_info.get('direct_distance', 0)
            route_distance = calculation_info.get('route_distance', float('inf'))
            effective_distance = calculation_info.get('effective_distance', 0)
            distance_type = calculation_info.get('distance_type', '직선거리_만')
            
            print(f"   📏 거리 정보:")
            print(f"      • 직선 거리: {direct_distance:.1f}m")
            if route_distance and route_distance != float('inf'):
                print(f"      • 경로 거리: {route_distance:.1f}m")
            print(f"      • 효과적 거리: {effective_distance:.1f}m ({distance_type})")
            
            # 3. 판단 과정
            reason = calculation_info.get('reason', '계산완료')
            print(f"   🎯 판단 과정:")
            print(f"      • 적용된 조건: {reason}")
            
            # 4. 위험도 조건 기준 설명
            print(f"   📋 조건 기준:")
            if is_approaching:
                print(f"      • 접근 중: 20m이하=HIGH, 50m이하=HIGH, 100m이하=MEDIUM, 그외=LOW")
            else:
                print(f"      • 멀어짐: 20m이하=HIGH, 40m이하=MEDIUM, 80m이하=LOW, 그외=LOW")
            
            # 5. 최종 결과
            print(f"   ✅ 계산 결과:")
            print(f"      • 원본: {raw_risk_level}")
            if stable_risk_level != raw_risk_level:
                print(f"      • 안정화: {stable_risk_level} ← 안정화 적용")
            else:
                print(f"      • 최종: {stable_risk_level}")
                
        except Exception as e:
            print(f"❌ 상세 분석 출력 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 BirdRiskSim 실시간 파이프라인 시작")
    print("=" * 60)
    
    # 파이프라인 생성 및 시작
    pipeline = RealTimePipeline()
    
    try:
        success = pipeline.start()
        if success:
            print("✅ 파이프라인이 정상적으로 종료되었습니다")
        else:
            print("❌ 파이프라인 시작 실패")
    except Exception as e:
        print(f"❌ 파이프라인 오류: {e}")
        pipeline.stop()

if __name__ == "__main__":
    main() 