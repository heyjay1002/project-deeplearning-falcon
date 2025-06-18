import sys
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage
import numpy as np
import cv2

# 상위 디렉토리들을 파이썬 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = current_dir
atc_gui_dir = os.path.dirname(tests_dir)
gui_dir = os.path.dirname(atc_gui_dir)

# 모든 필요한 경로 추가
for path in [atc_gui_dir, gui_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"현재 Python 경로:")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

try:
    from views.main_page import MainPage
    print("✓ MainPage import 성공")
except ImportError as e:
    print(f"✗ MainPage import 실패: {e}")
    sys.exit(1)

try:
    from utils.interface import DetectedObject, ObjectType, AirportZone, BirdRiskLevel, RunwayRiskLevel
    print("✓ interface 모듈 import 성공")
except ImportError as e:
    print(f"✗ interface 모듈 import 실패: {e}")
    # 기본값으로 대체
    DetectedObject = None
    ObjectType = None
    AirportZone = None
    BirdRiskLevel = None
    RunwayRiskLevel = None

try:
    from config.constants import MessagePrefix
    print("✓ constants 모듈 import 성공")
except ImportError as e:
    print(f"✗ constants 모듈 import 실패: {e}")
    MessagePrefix = None

class MockServer:
    """가상의 서버 클래스"""
    
    def __init__(self, main_page):
        self.main_page = main_page
        self.object_id_counter = 1
        self.setup_timers()
        
    def setup_timers(self):
        """타이머 설정"""
        # 모든 필요한 클래스가 import되었는지 확인
        if not all([DetectedObject, ObjectType, AirportZone, BirdRiskLevel, RunwayRiskLevel]):
            print("필요한 클래스들이 import되지 않아 타이머 설정을 건너뜁니다.")
            return
            
        # 객체 감지 이벤트 (2초마다)
        self.object_timer = QTimer()
        self.object_timer.timeout.connect(self.send_object_detection)
        self.object_timer.start(2000)
        
        # 조류 위험도 변경 (3초마다)
        self.bird_risk_timer = QTimer()
        self.bird_risk_timer.timeout.connect(self.send_bird_risk)
        self.bird_risk_timer.start(3000)
        
        # 활주로 위험도 변경 (5초마다)
        self.runway_risk_timer = QTimer()
        self.runway_risk_timer.timeout.connect(self.send_runway_risk)
        self.runway_risk_timer.start(5000)
        
        # CCTV 프레임 전송 (100ms마다)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.send_cctv_frame)
        self.frame_timer.start(100)
    
    def send_object_detection(self):
        """객체 감지 이벤트 전송"""
        if not DetectedObject:
            return
            
        try:
            # 테스트용 객체 생성
            obj = DetectedObject(
                object_id=self.object_id_counter,
                object_type=ObjectType.BIRD,
                x_coord=100.0,
                y_coord=200.0,
                zone=AirportZone.RWY_A,
                timestamp=datetime.now()
            )
            self.object_id_counter += 1
            
            # 객체 감지 이벤트 전송
            if hasattr(self.main_page, 'network_manager'):
                self.main_page.network_manager.object_detected.emit(obj)
        except Exception as e:
            print(f"객체 감지 이벤트 전송 오류: {e}")
    
    def send_bird_risk(self):
        """조류 위험도 변경 이벤트 전송"""
        if not BirdRiskLevel:
            return
            
        try:
            # 위험도 순환 (LOW -> MEDIUM -> HIGH -> LOW)
            current_risk = self.main_page.label_bird_risk_status.text()
            if current_risk == BirdRiskLevel.LOW.value:
                self.main_page.network_manager.bird_risk_changed.emit(BirdRiskLevel.MEDIUM)
            elif current_risk == BirdRiskLevel.MEDIUM.value:
                self.main_page.network_manager.bird_risk_changed.emit(BirdRiskLevel.HIGH)
            else:
                self.main_page.network_manager.bird_risk_changed.emit(BirdRiskLevel.LOW)
        except Exception as e:
            print(f"조류 위험도 변경 오류: {e}")
    
    def send_runway_risk(self):
        """활주로 위험도 변경 이벤트 전송"""
        if not RunwayRiskLevel:
            return
            
        try:
            # 활주로 A 위험도 토글
            current_risk = self.main_page.label_rwy1_status.text()
            if current_risk == RunwayRiskLevel.LOW.value:
                self.main_page.network_manager.runway_a_risk_changed.emit(RunwayRiskLevel.HIGH)
            else:
                self.main_page.network_manager.runway_a_risk_changed.emit(RunwayRiskLevel.LOW)
            
            # 활주로 B 위험도 토글
            current_risk = self.main_page.label_rwy2_status.text()
            if current_risk == RunwayRiskLevel.LOW.value:
                self.main_page.network_manager.runway_b_risk_changed.emit(RunwayRiskLevel.HIGH)
            else:
                self.main_page.network_manager.runway_b_risk_changed.emit(RunwayRiskLevel.LOW)
        except Exception as e:
            print(f"활주로 위험도 변경 오류: {e}")
    
    def send_cctv_frame(self):
        """CCTV 프레임 전송"""
        try:
            # 테스트용 이미지 생성
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"Test Frame {int(time.time())}", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # QImage로 변환
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # CCTV A, B 프레임 전송
            if hasattr(self.main_page, 'network_manager'):
                self.main_page.network_manager.frame_a_received.emit(q_image, int(time.time()))
                self.main_page.network_manager.frame_b_received.emit(q_image, int(time.time()))
        except Exception as e:
            print(f"CCTV 프레임 전송 오류: {e}")

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    try:
        # 메인 페이지 생성
        main_page = MainPage()
        main_page.show()
        print("✓ MainPage 생성 및 표시 성공")
        
        # 가상 서버 생성 및 시작
        mock_server = MockServer(main_page)
        print("✓ MockServer 생성 성공")
        
        # TCP 연결 상태 시뮬레이션
        if hasattr(main_page, 'network_manager'):
            QTimer.singleShot(1000, lambda: main_page.network_manager.tcp_connection_status_changed.emit(True, "연결됨"))
            # UDP 연결 상태 시뮬레이션
            QTimer.singleShot(2000, lambda: main_page.network_manager.udp_connection_status_changed.emit(True, "연결됨"))
            print("✓ 네트워크 시뮬레이션 설정 완료")
        
    except Exception as e:
        print(f"✗ 초기화 중 오류 발생: {e}")
        return 1
    
    print("🚀 애플리케이션 시작")
    return app.exec()

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)