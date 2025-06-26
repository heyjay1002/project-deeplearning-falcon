#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
최초 감지 알림 테스트 파일
서버 없이도 최초 감지 알림 기능을 테스트할 수 있습니다.
"""

import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.interface import DetectedObject, ObjectType, AirportArea, EventType
from views.notification_dialog import NotificationDialog
from views.main_page import MainPage
from main import WindowClass


class FirstDetectionTester(QWidget):
    """최초 감지 알림 테스트 위젯"""
    
    def __init__(self):
        super().__init__()
        self.main_window = None
        self.test_object_id = 1
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("최초 감지 알림 테스트")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        # 안내 라벨
        info_label = QLabel("최초 감지 알림 테스트")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(info_label)
        
        # 메인 윈도우 열기 버튼
        self.open_main_btn = QPushButton("메인 윈도우 열기")
        self.open_main_btn.clicked.connect(self.open_main_window)
        layout.addWidget(self.open_main_btn)
        
        # 테스트 버튼들
        self.test_person_btn = QPushButton("일반인 최초 감지 테스트")
        self.test_person_btn.clicked.connect(self.test_person_detection)
        self.test_person_btn.setEnabled(False)
        layout.addWidget(self.test_person_btn)
        
        self.test_vehicle_btn = QPushButton("일반차량 최초 감지 테스트")
        self.test_vehicle_btn.clicked.connect(self.test_vehicle_detection)
        self.test_vehicle_btn.setEnabled(False)
        layout.addWidget(self.test_vehicle_btn)
        
        self.test_bird_btn = QPushButton("조류 최초 감지 테스트")
        self.test_bird_btn.clicked.connect(self.test_bird_detection)
        self.test_bird_btn.setEnabled(False)
        layout.addWidget(self.test_bird_btn)
        
        self.test_multiple_btn = QPushButton("여러 객체 동시 감지 테스트")
        self.test_multiple_btn.clicked.connect(self.test_multiple_detection)
        self.test_multiple_btn.setEnabled(False)
        layout.addWidget(self.test_multiple_btn)
        
        # 직접 알림 다이얼로그 테스트
        self.test_dialog_btn = QPushButton("알림 다이얼로그 직접 테스트")
        self.test_dialog_btn.clicked.connect(self.test_notification_dialog_directly)
        layout.addWidget(self.test_dialog_btn)
        
        # 상태 라벨
        self.status_label = QLabel("메인 윈도우를 먼저 열어주세요.")
        self.status_label.setStyleSheet("color: gray; margin: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def open_main_window(self):
        """메인 윈도우 열기"""
        try:
            self.main_window = WindowClass()
            self.main_window.show()
            
            # 테스트 버튼들 활성화
            self.test_person_btn.setEnabled(True)
            self.test_vehicle_btn.setEnabled(True)
            self.test_bird_btn.setEnabled(True)
            self.test_multiple_btn.setEnabled(True)
            self.open_main_btn.setEnabled(False)
            
            self.status_label.setText("메인 윈도우가 열렸습니다. 테스트 버튼을 사용하세요.")
            self.status_label.setStyleSheet("color: green; margin: 10px;")
            
        except Exception as e:
            self.status_label.setText(f"메인 윈도우 열기 실패: {e}")
            self.status_label.setStyleSheet("color: red; margin: 10px;")
    
    def create_test_object(self, object_type: ObjectType, area: AirportArea) -> DetectedObject:
        """테스트용 DetectedObject 생성"""
        obj = DetectedObject(
            event_type=EventType.UNAUTH,  # "출입 위반"
            object_id=self.test_object_id,
            object_type=object_type,
            x_coord=100.0 + (self.test_object_id * 10),
            y_coord=150.0 + (self.test_object_id * 5),
            area=area,
            timestamp=datetime.now(),
            state_info=None,
            image_data=None
        )
        self.test_object_id += 1
        return obj
    
    def test_person_detection(self):
        """일반인 최초 감지 테스트"""
        if not self.main_window:
            return
            
        obj = self.create_test_object(ObjectType.PERSON, AirportArea.RWY_A)
        self.simulate_first_detection([obj])
        self.status_label.setText(f"일반인 최초 감지 테스트 실행 (ID: {obj.object_id})")
    
    def test_vehicle_detection(self):
        """일반차량 최초 감지 테스트"""
        if not self.main_window:
            return
            
        obj = self.create_test_object(ObjectType.VEHICLE, AirportArea.TWY_A)
        self.simulate_first_detection([obj])
        self.status_label.setText(f"일반차량 최초 감지 테스트 실행 (ID: {obj.object_id})")
    
    def test_bird_detection(self):
        """조류 최초 감지 테스트"""
        if not self.main_window:
            return
            
        obj = self.create_test_object(ObjectType.BIRD, AirportArea.RWY_B)
        self.simulate_first_detection([obj])
        self.status_label.setText(f"조류 최초 감지 테스트 실행 (ID: {obj.object_id})")
    
    def test_multiple_detection(self):
        """여러 객체 동시 감지 테스트"""
        if not self.main_window:
            return
            
        objects = [
            self.create_test_object(ObjectType.PERSON, AirportArea.RWY_A),
            self.create_test_object(ObjectType.VEHICLE, AirportArea.TWY_A),
            self.create_test_object(ObjectType.BIRD, AirportArea.RWY_B)
        ]
        
        self.simulate_first_detection(objects)
        object_ids = [str(obj.object_id) for obj in objects]
        self.status_label.setText(f"다중 객체 최초 감지 테스트 실행 (IDs: {', '.join(object_ids)})")
    
    def simulate_first_detection(self, objects):
        """최초 감지 이벤트 시뮬레이션"""
        try:
            # MainPage의 최초 감지 처리 메서드 직접 호출
            main_page = self.main_window.main_page
            if hasattr(main_page, 'on_first_object_detected'):
                # 각 객체에 대해 개별적으로 호출 (메서드가 단일 객체를 받음)
                for obj in objects:
                    main_page.on_first_object_detected(obj)
            else:
                self.status_label.setText("MainPage에 on_first_object_detected 메서드가 없습니다.")
                self.status_label.setStyleSheet("color: red; margin: 10px;")
                
        except Exception as e:
            self.status_label.setText(f"시뮬레이션 오류: {e}")
            self.status_label.setStyleSheet("color: red; margin: 10px;")
    
    def test_notification_dialog_directly(self):
        """알림 다이얼로그 직접 테스트"""
        try:
            # 테스트용 객체 생성
            test_obj = self.create_test_object(ObjectType.PERSON, AirportArea.RWY_A)
            
            # NotificationDialog 직접 생성 및 표시
            dialog = NotificationDialog(
                notification_type="unauth",  # "출입 위반"
                data={
                    'object': test_obj,
                    'message': f"출입 위반 감지: {test_obj.object_type.value} (ID: {test_obj.object_id})"
                }
            )
            dialog.exec()
            
            self.status_label.setText("알림 다이얼로그 직접 테스트 완료")
            self.status_label.setStyleSheet("color: blue; margin: 10px;")
            
        except Exception as e:
            self.status_label.setText(f"다이얼로그 테스트 오류: {e}")
            self.status_label.setStyleSheet("color: red; margin: 10px;")


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 테스트 윈도우 생성
    tester = FirstDetectionTester()
    tester.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 