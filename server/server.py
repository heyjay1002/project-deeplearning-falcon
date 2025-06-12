"""
YOLO 객체 검지 서버 메인 윈도우
카메라별 객체 검지 결과를 표시
"""

import sys
import cv2
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from falcon.video_communicator import VideoCommunicator
from falcon.video_processor import VideoProcessor
from falcon.detection_communicator import DetectionCommunicator

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
        self.detection_stats_label = QLabel('감지: 0 FPS, 처리 시간: 0ms')
        self.buffer_status_label = QLabel('버퍼: 0/0 프레임')
        
        layout.addWidget(self.video_stats_label)
        layout.addWidget(self.detection_stats_label)
        layout.addWidget(self.buffer_status_label)
    
    def _init_threads(self):
        """스레드 초기화"""
        # 검지 결과 버퍼 (스레드 간 공유)
        self.detection_buffer = {}
        
        # 검지 결과 처리 스레드
        self.processor_thread = VideoProcessor(self.detection_buffer)
        
        # 비디오 통신 스레드
        self.video_thread = VideoCommunicator(self.processor_thread)
        self.video_thread.server_frame_ready.connect(self.update_frame)
        self.video_thread.server_stats_ready.connect(self.update_video_stats)
        self.video_thread.server_buffer_status_ready.connect(self.update_buffer_status)
        
        # IDS 통신 스레드
        self.detection_thread = DetectionCommunicator(self.detection_buffer)
        self.detection_thread.stats_ready.connect(self.update_detection_stats)
        
        # 스레드 시작
        print("[INFO] 서버 시작")
        self.processor_thread.start()  # VideoProcessor를 먼저 시작
        self.video_thread.start()
        self.detection_thread.start()
    
    def update_frame(self, frame_data):
        """프레임 업데이트
        
        Args:
            frame_data (dict): 프레임 데이터
                - frame: 검지 결과가 그려진 프레임
                - detections: 검지 결과 리스트
                - seq: 프레임 시퀀스 번호
        """
        frame = frame_data['frame']
        
        # OpenCV BGR 이미지를 Qt QImage로 변환
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        
        # QImage를 QPixmap으로 변환하여 화면에 표시
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(scaled_pixmap)
    
    def update_video_stats(self, stats):
        """비디오 통계 업데이트
        
        Args:
            stats (dict): 통계 정보
                - fps: 현재 FPS
                - seq: 현재 프레임 시퀀스 번호
                - total_frames: 총 수신 프레임 수
        """
        self.video_stats_label.setText(
            f"비디오: {stats['fps']} FPS (seq: {stats['seq']}, total: {stats['total_frames']})"
        )
    
    def update_detection_stats(self, stats):
        """검지 통계 업데이트
        
        Args:
            stats (dict): 통계 정보
                - fps: 검지 FPS
                - processing_time: 프레임당 처리 시간 (ms)
        """
        self.detection_stats_label.setText(
            f"감지: {stats['fps']} FPS, 처리 시간: {stats['processing_time']}ms"
        )
    
    def update_buffer_status(self, status):
        """버퍼 상태 업데이트
        
        Args:
            status (str): 버퍼 상태 문자열
        """
        self.buffer_status_label.setText(status)
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트 처리"""
        print("[INFO] 서버 종료")
        self.video_thread.stop()
        self.processor_thread.stop()
        self.detection_thread.stop()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 