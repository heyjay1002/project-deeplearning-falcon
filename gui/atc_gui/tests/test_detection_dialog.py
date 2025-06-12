import sys
import os
from PyQt6.QtWidgets import QApplication
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.object_detection_dialog import ObjectDetectionDialog
from models.detected_object import DetectedObject, ObjectType, AirportZone

def test_detection_dialog():
    # 테스트용 객체 생성
    test_obj = DetectedObject(
        object_id=1,
        object_type=ObjectType.BIRD,
        zone=AirportZone.RWY_A,
        x_coord=100,
        y_coord=200,
        timestamp=datetime.now()
    )
    
    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    
    # 다이얼로그 생성 및 표시
    dialog = ObjectDetectionDialog(test_obj)
    dialog.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    test_detection_dialog() 