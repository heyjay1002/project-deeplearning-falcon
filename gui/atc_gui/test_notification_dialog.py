#!/usr/bin/env python3
"""
NotificationDialog 테스트 스크립트
"""

import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from views.notification_dialog import NotificationDialog
from utils.interface import DetectedObject, ObjectType, Airportarea

class TestData:
    """테스트용 데이터 클래스"""
    def __init__(self, object_id, object_type, area, timestamp=None, image_data=None, state_info=None):
        self.object_id = object_id
        self.object_type = object_type
        self.area = area
        self.timestamp = timestamp or datetime.now()
        self.image_data = image_data
        self.state_info = state_info

class TestWindow(QMainWindow):
    """테스트용 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotificationDialog 테스트")
        self.setGeometry(100, 100, 400, 300)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃 설정
        layout = QVBoxLayout(central_widget)
        
        # 제목
        title_label = QLabel("NotificationDialog 테스트")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 테스트 버튼들
        self.create_test_button(layout, "위험요소 감지 알림 (이미지 있음)", self.test_object_detection_with_image)
        self.create_test_button(layout, "위험요소 감지 알림 (이미지 없음)", self.test_object_detection_no_image)
        self.create_test_button(layout, "출입 위반 알림", self.test_violation_access)
        
        # 설명
        info_label = QLabel("버튼을 클릭하면 해당 알림 다이얼로그가 표시됩니다.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(info_label)
        
    def create_test_button(self, layout, text, callback):
        """테스트 버튼 생성"""
        button = QPushButton(text)
        button.clicked.connect(callback)
        button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        layout.addWidget(button)
    
    def create_test_image(self):
        """테스트용 이미지 생성"""
        # 간단한 테스트 이미지 생성 (100x80 크기)
        image = QImage(100, 80, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.lightGray)
        
        # 간단한 도형 그리기
        from PyQt6.QtGui import QPainter, QPen, QColor
        painter = QPainter(image)
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawRect(10, 10, 80, 60)
        painter.drawText(20, 40, "TEST")
        painter.end()
        
        # QImage를 바이트로 변환
        byte_array = image.bits().asarray(image.width() * image.height() * 4)
        return bytes(byte_array)
    
    def test_object_detection_with_image(self):
        """이미지가 있는 위험요소 감지 알림 테스트"""
        test_data = TestData(
            object_id=12345,
            object_type=ObjectType.PERSON,
            area=Airportarea.RUNWAY_A,
            timestamp=datetime.now(),
            image_data=self.create_test_image(),
            state_info="정상"
        )
        
        dialog = NotificationDialog('object', test_data, self)
        dialog.show()
    
    def test_object_detection_no_image(self):
        """이미지가 없는 위험요소 감지 알림 테스트"""
        test_data = TestData(
            object_id=67890,
            object_type=ObjectType.BIRD,
            area=Airportarea.RUNWAY_B,
            timestamp=datetime.now(),
            image_data=None,
            state_info="위험"
        )
        
        dialog = NotificationDialog('object', test_data, self)
        dialog.show()
    
    def test_violation_access(self):
        """출입 위반 알림 테스트"""
        test_data = TestData(
            object_id=11111,
            object_type=ObjectType.PERSON,
            area=Airportarea.RESTRICTED,
            timestamp=datetime.now(),
            image_data=self.create_test_image(),
            state_info="출입 위반"
        )
        
        dialog = NotificationDialog('violation_access', test_data, self)
        dialog.show()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 테스트 윈도우 생성 및 표시
    window = TestWindow()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 