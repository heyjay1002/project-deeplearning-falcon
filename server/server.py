"""
YOLO 객체 검지 서버 메인 윈도우
카메라별 객체 검지 결과를 표시
"""

import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from falcon.udp_stream import VideoCommunicator
from falcon.video_processor import VideoProcessor
from falcon.detection_processor import DetectionProcessor
from falcon.tcp_stream import DetectionCommunicator
import config

class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    def __init__(self):
        super().__init__()
        self.initUI()
        self._init_threads()
    
    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle('YOLO Object Detection Server')
        self.setGeometry(100, 100, 800, 600)

        # 메인 위젯과 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 비디오 표시 레이블
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        # 상태 표시 레이블들
        self.video_stats_label = QLabel('비디오: 0 FPS')
        self.detection_stats_label = QLabel('감지: 0 FPS')
        self.buffer_status_label = QLabel('버퍼: 0/0 프레임')
        
        layout.addWidget(self.video_stats_label)
        layout.addWidget(self.detection_stats_label)
        layout.addWidget(self.buffer_status_label)
        
        # 프레임 크기 표시 레이블 추가
        self.frame_size_label = QLabel('프레임 크기: - x -')
        layout.addWidget(self.frame_size_label)
    
    def _init_threads(self):
        """스레드 초기화"""
        # 비디오 프로세서 스레드
        self.video_processor = VideoProcessor()
        self.video_processor.frame_processed.connect(self._on_frame_processed)
        self.video_processor.stats_ready.connect(self.update_video_stats)
        self.video_processor.buffer_status_ready.connect(self.update_buffer_status)
        
        # 검출 프로세서 스레드
        self.detection_processor = DetectionProcessor(video_processor=self.video_processor)
        self.detection_processor.detection_processed.connect(self._on_detection_processed)
        self.detection_processor.stats_ready.connect(self.update_detection_stats)
        
        # 비디오 통신 스레드
        self.video_thread = VideoCommunicator()
        self.video_thread.frame_received.connect(self.video_processor.process_frame)
        
        # IDS 통신 스레드
        self.detection_thread = DetectionCommunicator(repository=self.detection_processor.repository)
        self.detection_thread.detection_received.connect(self.detection_processor.process_detection)
        
        # 비디오 통신기 연결
        self.detection_thread.set_video_communicator(self.video_thread)
        
        # 스레드 시작
        print("[INFO] 서버 시작")
        self.video_processor.start()
        self.detection_processor.start()
        self.video_thread.start()
        self.detection_thread.start()
    
    def _on_frame_processed(self, frame_data):
        """프레임 처리 완료 시 호출
        Args:
            frame_data (dict): 처리된 프레임 데이터
                - frame: 원본 프레임
                - img_id: 이미지 ID
                - cam_id: 카메라 ID
        """
        frame = frame_data['frame']
        img_id = frame_data['img_id']
        cam_id = frame_data.get('cam_id', 'A')
        
        # 검출 결과 그리기
        frame_with_boxes = self.detection_processor.draw_detections(frame, img_id)
        
        # 활주로 구역 그리기 (디버깅용)
        # self.draw_runway_zones(frame_with_boxes)
        
        # OpenCV BGR 이미지를 Qt QImage로 변환
        height, width, channel = frame_with_boxes.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame_with_boxes.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        
        # QImage를 QPixmap으로 변환하여 화면에 표시
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(scaled_pixmap)

        # 박스가 그려진 프레임을 VideoCommunicator로 전달하여 UDP 송출
        self.video_thread.send_frame_with_boxes(frame_with_boxes, cam_id, img_id)
        
        # 프레임 크기 표시 갱신
        if config.frame_width and config.frame_height:
            self.frame_size_label.setText(f'프레임 크기: {config.frame_width} x {config.frame_height}')
    
    def _on_detection_processed(self, detection_data):
        """검출 처리 완료 시 호출"""
        pass  # 필요한 경우 여기에 추가 처리 구현
    
    def update_video_stats(self, stats):
        """비디오 통계 업데이트"""
        self.video_stats_label.setText(f"비디오: {stats['fps']} FPS")
    
    def update_detection_stats(self, stats):
        """검출 통계 업데이트"""
        self.detection_stats_label.setText(f"감지: {stats['fps']} FPS")
    
    def update_buffer_status(self, status):
        """버퍼 상태 업데이트"""
        self.buffer_status_label.setText(status)
    
    def draw_runway_zones(self, frame):
        """활주로 A, B 구역을 상수로 간단하게 그리기 (디버깅용)"""
        height, width = frame.shape[:2]
        
        # 활주로 A (상단): y=0~22%
        rwy_a_y1 = 0
        rwy_a_y2 = int(0.22 * height)
        cv2.rectangle(frame, (0, rwy_a_y1), (width, rwy_a_y2), (0, 0, 255), 3)
        cv2.putText(frame, "RUNWAY A", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # 활주로 B (중간): y=52~70%  
        rwy_b_y1 = int(0.52 * height)
        rwy_b_y2 = int(0.70 * height)
        cv2.rectangle(frame, (0, rwy_b_y1), (width, rwy_b_y2), (255, 0, 0), 3)
        cv2.putText(frame, "RUNWAY B", (10, rwy_b_y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
    
    def closeEvent(self, event):
        """윈도우 종료 시 호출"""
        # 모든 스레드 종료
        self.video_thread.stop()
        self.detection_thread.stop()
        self.video_processor.quit()
        self.detection_processor.quit()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 