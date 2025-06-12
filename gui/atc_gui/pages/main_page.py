from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6 import uic
from PyQt6.QtGui import QPixmap, QColor, QImage
from PyQt6.QtCore import Qt, QTimer
import os
from pages.object_detail_dialog import ObjectDetailDialog
from pages.object_detection_dialog import ObjectDetectionDialog
from models.detected_object import DetectedObject
from config import BirdRiskLevel, RunwayRiskLevel, Constants, ObjectType, AirportZone
from utils.tcp_client import TcpClient
from utils.udp_client import UdpClient
from utils.interface import MessageInterface
from widgets.map_marker_widget import MapMarkerWidget
from utils.logger import logger

class MainPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/main_page.ui')
        uic.loadUi(ui_path, self)

        # 이미지 경로
        base_dir = os.path.dirname(__file__)
        self.map_path = os.path.join(base_dir, '../resources/images/map.png')
        self.marker_icon_path = os.path.join(base_dir, '../resources/images/bird.png')

        # 원본 이미지 저장
        self.map_pixmap = QPixmap(self.map_path)

        # 초기 이미지 설정
        self.update_images()

        # 테이블 설정
        self.setup_table()
        
        # TCP 클라이언트 설정
        self.setup_tcp_client()
        
        # UDP 클라이언트 설정
        self.setup_udp_client()

        # 마커 오버레이 연동
        self.setup_marker_overlay()

        # 버튼 연결
        self.setup_buttons()

        # 상세보기 다이얼로그 설정
        self.setup_detail_dialog()

        # 첫 객체 감지 여부를 추적하는 변수
        self.is_first_detection = True

    def setup_table(self):
        """테이블 초기 설정"""
        # 컬럼 헤더 설정
        headers = ["ID", "위치", "종류"]
        self.table_object_list.setColumnCount(len(headers))
        self.table_object_list.setHorizontalHeaderLabels(headers)
        
        # 선택 모드 설정
        self.table_object_list.setSelectionBehavior(self.table_object_list.SelectionBehavior.SelectRows)
        
        # 초기 데이터 클리어
        self.table_object_list.setRowCount(0)

    def setup_tcp_client(self):
        """TCP 클라이언트 설정 및 시그널 연결"""
        self.tcp_client = TcpClient()
        
        # 시그널 연결
        self.tcp_client.object_detected.connect(self.update_object_list)
        self.tcp_client.bird_risk_changed.connect(self.update_bird_risk)
        self.tcp_client.runway_a_risk_changed.connect(self.update_runway_a_risk)
        self.tcp_client.runway_b_risk_changed.connect(self.update_runway_b_risk)
        self.tcp_client.object_detail_response.connect(self.update_object_detail)
        self.tcp_client.object_detail_error.connect(self.handle_object_detail_error)

    def setup_udp_client(self):
        """UDP 클라이언트 설정 및 시그널 연결"""
        self.udp_client = UdpClient()
        self.udp_client.frame_received.connect(self.update_cctv_frame)
        self.udp_client.connect()

    def setup_marker_overlay(self):
        """마커 오버레이 설정"""
        self.map_marker = MapMarkerWidget(self.map_overlay_frame)
        layout = self.map_overlay_frame.layout()
        idx = layout.indexOf(self.marker_overlay_placeholder)
        layout.removeWidget(self.marker_overlay_placeholder)
        self.marker_overlay_placeholder.deleteLater()
        layout.addWidget(self.map_marker, 0, 0)
        
        # 지도 이미지 설정
        self.map_marker.set_map_image(self.map_path)
    def setup_buttons(self):
        """버튼 시그널 연결"""
        self.btn_show_map.clicked.connect(self.show_map)
        self.btn_show_cctv.clicked.connect(self.show_cctv)
        self.btn_detail.clicked.connect(self.show_detail)

    def setup_detail_dialog(self):
        """상세보기 다이얼로그 설정"""
        self.object_detail_dialog = ObjectDetailDialog(self)
        self.object_area.addWidget(self.object_detail_dialog)
        self.object_detail_dialog.btn_back.clicked.connect(self.show_table)

    def update_object_list(self, objects: list[DetectedObject]):
        """객체 목록 업데이트"""
        logger.debug(f"객체 목록 업데이트: {len(objects)}개 객체")
        self.table_object_list.setRowCount(len(objects))
        
        for row, obj in enumerate(objects):
            # ID
            self.table_object_list.setItem(row, 0, QTableWidgetItem(str(obj.object_id)))
            # 위치
            self.table_object_list.setItem(row, 1, QTableWidgetItem(obj.zone.value))
            # 종류
            self.table_object_list.setItem(row, 2, QTableWidgetItem(obj.object_type.value))

        # 마커 업데이트
        self.update_markers(objects)

        # 첫 객체 감지 시 팝업 표시
        if self.is_first_detection and objects:
            self.is_first_detection = False
            logger.info("첫 번째 객체 감지")
            dialog = ObjectDetectionDialog(objects[0], self)
            dialog.exec()

    def update_markers(self, objects: list[DetectedObject]):
        """마커 업데이트"""
        logger.debug(f"마커 업데이트: {len(objects)}개 객체")
        self.map_marker.clear_markers()
        
        for obj in objects:
            self.map_marker.add_marker(
                obj.x_coord, 
                obj.y_coord, 
                self.marker_icon_path, 
                obj.object_id,
                self.select_table_row
            )

    def update_bird_risk(self, risk_level: BirdRiskLevel):
        """조류 위험도 업데이트"""
        logger.info(f"조류 위험도 변경: {risk_level.value}")
        self.label_bird_risk_status.setText(risk_level.value)
        self.label_bird_risk_status.setStyleSheet(
            f"background-color: {Constants.RISK_COLORS[risk_level]}; "
            f"color: {'#000000' if risk_level == BirdRiskLevel.MEDIUM else '#FFFFFF'}; "
            "font-weight: bold;"
        )

    def update_runway_a_risk(self, risk_level: RunwayRiskLevel):
        """활주로 A 위험도 업데이트"""
        logger.info(f"활주로 A 위험도 변경: {risk_level.value}")
        self.label_rwy1_status.setText(risk_level.value)
        self.label_rwy1_status.setStyleSheet(
            f"background-color: {Constants.RISK_COLORS[risk_level]}; "
            f"color: {'#000000' if risk_level == RunwayRiskLevel.MEDIUM else '#FFFFFF'}; "
            "font-weight: bold;"
        )

    def update_runway_b_risk(self, risk_level: RunwayRiskLevel):
        """활주로 B 위험도 업데이트"""
        logger.info(f"활주로 B 위험도 변경: {risk_level.value}")
        self.label_rwy2_status.setText(risk_level.value)
        self.label_rwy2_status.setStyleSheet(
            f"background-color: {Constants.RISK_COLORS[risk_level]}; "
            f"color: {'#000000' if risk_level == RunwayRiskLevel.MEDIUM else '#FFFFFF'}; "
            "font-weight: bold;"
        )

    def update_object_detail(self, obj: DetectedObject):
        """객체 상세 정보 업데이트"""
        logger.debug(f"객체 상세 정보 업데이트: ID {obj.object_id}")
        info = f"객체 ID: {obj.object_id}\n"
        info += f"종류: {obj.object_type.value}\n"
        info += f"위치: {obj.zone.value}\n"
        info += f"발견 시각: {obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if obj.extra_info:
            info += f"\n추가 정보: {obj.extra_info}"
            
        self.object_detail_dialog.detail_info.setText(info)
        
        if obj.image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(obj.image_data)
            self.object_detail_dialog.detail_img.setPixmap(
                pixmap.scaled(
                    self.object_detail_dialog.detail_img.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        
        self.object_area.setCurrentIndex(2)

    def handle_object_detail_error(self, error_msg: str):
        """객체 상세보기 오류 처리"""
        logger.error(f"객체 상세보기 오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"객체 상세보기 오류: {error_msg}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_images()

    def update_images(self):
        """이미지 업데이트"""
        logger.debug("이미지 업데이트")
        # 지도 이미지 업데이트
        if not self.map_pixmap.isNull():
            self.label_map.setPixmap(self.map_pixmap.scaled(
                self.label_map.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def select_table_row(self, row_idx):
        """테이블 행 선택"""
        logger.debug(f"테이블 행 선택: {row_idx}")
        self.table_object_list.selectRow(row_idx)

    def show_map(self):
        """지도 보기"""
        logger.debug("지도 보기")
        self.map_cctv_stack.setCurrentIndex(0)

    def show_cctv(self):
        """CCTV 보기"""
        idx = self.combo_cctv.currentIndex()
        logger.debug(f"CCTV 보기: {idx + 1}")
        self.map_cctv_stack.setCurrentIndex(idx + 1)
        
        # TCP 클라이언트를 통해 CCTV 영상 요청
        if idx == 0:
            camera_id = "A"
        elif idx == 1:
            camera_id = "B"
        self.tcp_client.send_message(MessageInterface.create_cctv_request(camera_id))

    def show_table(self):
        """테이블 보기"""
        logger.debug("테이블 보기")
        self.object_area.setCurrentIndex(0)

    def show_detail(self):
        """상세보기"""
        row = self.table_object_list.currentRow()
        if row < 0:
            logger.warning("선택된 객체가 없음")
            return
            
        object_id = int(self.table_object_list.item(row, 0).text())
        logger.debug(f"객체 상세보기 요청: ID {object_id}")
        self.tcp_client.request_object_detail(object_id)

    def update_cctv_frame(self, frame: QImage):
        """CCTV 프레임 업데이트"""
        # 현재 선택된 CCTV 화면에 프레임 표시
        current_index = self.map_cctv_stack.currentIndex()
        if current_index == 1:  # CCTV 1
            self.label_cctv_1.setPixmap(QPixmap.fromImage(frame).scaled(
                self.label_cctv_1.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        elif current_index == 2:  # CCTV 2
            self.label_cctv_2.setPixmap(QPixmap.fromImage(frame).scaled(
                self.label_cctv_2.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def closeEvent(self, event):
        """위젯 종료 시 처리"""
        self.udp_client.disconnect()
        super().closeEvent(event)

    # TCP 연결 관련 함수 (ui에 연결/해제 버튼 추가)

    # 명령어 전송 관련 함수
    