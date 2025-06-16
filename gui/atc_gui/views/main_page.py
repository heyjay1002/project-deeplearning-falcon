from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6 import uic
from PyQt6.QtGui import QPixmap, QColor, QImage
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import os
from datetime import datetime
from views.object_detail_dialog import ObjectDetailDialog
from views.object_detection_dialog import ObjectDetectionDialog
from models.detected_object import DetectedObject
from config import BirdRiskLevel, RunwayRiskLevel, Constants, ObjectType, AirportZone
from config.settings import Settings
from utils.network_manager import NetworkManager
from utils.udp_client import UdpClient
from widgets.map_marker_widget import MapMarkerWidget, MarkerData, MarkerType, MarkerState
from utils.logger import logger
import cv2
import time
from collections import deque

class MainPage(QWidget):
    # 객체 목록 업데이트 시그널 추가
    object_list_updated = pyqtSignal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/main_page.ui')
        uic.loadUi(ui_path, self)

        # 현재 처리된 객체 ID 저장
        self.current_object_ids = set()

        # 설정 로드
        self.settings = Settings.get_instance()

        # 프레임 버퍼 및 디스플레이 타이머 초기화
        self.frame_buffer = {'A': deque(maxlen=5), 'B': deque(maxlen=5)}
        self.target_fps = 10  # 필요시 settings에서 가져와도 됨
        self.frame_display_timer = QTimer(self)
        self.frame_display_timer.timeout.connect(self.display_latest_frames)
        self.frame_display_timer.start(int(1000 / self.target_fps))
        
        # 마지막으로 표시한 이미지ID 저장
        self.last_displayed_image_id = {'A': -1, 'B': -1}

        # 이미지 경로 설정 및 검증
        self.setup_image_paths()

        # 초기 이미지 설정
        self.setup_map_display()

        # 테이블 설정
        self.setup_table()
        
        # 네트워크 관리자 설정
        self.setup_network_manager()

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

        # 객체 업데이트 최적화를 위한 변수들
        self.pending_objects = []  # 대기 중인 객체 목록
        self.last_update_time = 0  # 마지막 업데이트 시간
        self.update_timer = QTimer(self)  # 업데이트 타이머
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.update_timer.start(self.settings.data.object_update_interval)  # 설정된 간격으로 업데이트 처리

        # 스택 위젯 초기 상태 설정
        self.map_cctv_stack.setCurrentIndex(0)  # 지도 페이지로 시작
        logger.info("MainPage 초기화 완료")

    def setup_image_paths(self):
        """이미지 경로 설정"""
        base_dir = os.path.dirname(__file__)
        self.map_path = os.path.join(base_dir, '../resources/images/map_crop.png')
        self.marker_icon_path = os.path.join(base_dir, '../resources/images/bird.png')

    def setup_map_display(self):
        """지도 표시 설정"""
        # 지도 이미지 로드
        self.map_pixmap = QPixmap()
        
        if os.path.exists(self.map_path):
            if self.map_pixmap.load(self.map_path):
                pass  # 로드 성공
            else:
                # 임시 이미지 생성
                self.create_placeholder_map()
        else:
            # 임시 이미지 생성
            self.create_placeholder_map()

        # 초기 이미지 표시
        self.update_map_image()

    def create_placeholder_map(self):
        """임시 지도 이미지 생성"""
        self.map_pixmap = QPixmap(800, 600)
        self.map_pixmap.fill(Qt.GlobalColor.lightGray)
        
        # 텍스트 추가
        from PyQt6.QtGui import QPainter, QPen
        painter = QPainter(self.map_pixmap)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawText(self.map_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 
                        "지도 이미지를 로드할 수 없습니다\n경로를 확인하세요")
        painter.end()

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

    def setup_network_manager(self):
        """네트워크 관리자 설정 및 시그널 연결"""
        self.network_manager = NetworkManager(self)
        
        # 네트워크 관리자의 시그널을 UI 메서드에 연결
        self.network_manager.object_detected.connect(self.update_object_list)
        self.network_manager.bird_risk_changed.connect(self.update_bird_risk)
        self.network_manager.runway_a_risk_changed.connect(self.update_runway_a_risk)
        self.network_manager.runway_b_risk_changed.connect(self.update_runway_b_risk)
        self.network_manager.object_detail_response.connect(self.update_object_detail)
        self.network_manager.object_detail_error.connect(self.handle_object_detail_error)
        self.network_manager.frame_a_received.connect(self.update_cctv_a_frame)
        self.network_manager.frame_b_received.connect(self.update_cctv_b_frame)
        self.network_manager.tcp_connection_status_changed.connect(self.update_tcp_connection_status)
        self.network_manager.udp_connection_status_changed.connect(self.update_udp_connection_status)

        # 네트워크 서비스 시작
        self.network_manager.start_services()

    def setup_status_bar(self):
        """커스텀 상태바 위젯 설정 (TCP/UDP 상태만)"""
        main_window = self.window()  # QMainWindow 인스턴스 가져오기
        if hasattr(main_window, 'statusBar'):
            status_bar = main_window.statusBar()
            # 이미 라벨이 있으면 중복 추가 방지
            if not hasattr(self, 'tcp_status_label'):
                self.tcp_status_label = QLabel("TCP ●")
                self.udp_status_label = QLabel("UDP ●")
                self.tcp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")
                self.udp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")
                status_bar.addWidget(self.tcp_status_label)
                status_bar.addWidget(self.udp_status_label)

    def update_tcp_connection_status(self, is_connected: bool, message: str):
        """TCP 연결 상태 UI 업데이트 (메시지 라벨 제거)"""
        logger.info(f"TCP 연결 상태 변경: {message}")
        if hasattr(self, 'tcp_status_label'):
            if is_connected:
                self.tcp_status_label.setStyleSheet("color: green; font-weight: bold; margin-right: 8px;")
            else:
                self.tcp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")

    def update_udp_connection_status(self, is_connected: bool, message: str):
        """UDP 연결 상태 UI 업데이트 (메시지 라벨 제거)"""
        logger.info(f"UDP 연결 상태 변경: {message}")
        if hasattr(self, 'udp_status_label'):
            if is_connected:
                self.udp_status_label.setStyleSheet("color: green; font-weight: bold; margin-right: 8px;")
            else:
                self.udp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")

    def setup_udp_client(self):
        """UDP 클라이언트 설정"""
        self.udp_client = UdpClient()
        self.udp_client.set_max_fps(self.target_fps)  # 설정된 FPS 적용
        self.udp_client.frame_received.connect(self.handle_udp_frame)
        self.udp_client.connection_status_changed.connect(self.update_udp_connection_status)
        logger.info("UDP 클라이언트 초기화 완료 (연결은 CCTV 요청 시)")

    def handle_udp_frame(self, cam_id: str, frame, image_id: int = None):
        """UDP로 수신된 프레임 처리"""
        try:            
            self.last_displayed_image_id[cam_id] = image_id
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            if q_image.isNull():
                return
                
            # 이미지ID와 함께 저장
            self.frame_buffer[cam_id].append((image_id, q_image))
            
        except Exception as e:
            logger.error(f"UDP 프레임 처리 오류: {str(e)}")

    def display_latest_frames(self):
        """가장 최신 프레임 표시"""
        for cam_id in ['A', 'B']:
            if self.frame_buffer[cam_id]:
                # 가장 최신 프레임만 꺼내서 디스플레이
                _, latest_frame = self.frame_buffer[cam_id][-1]
                if cam_id == 'A':
                    self.update_cctv_a_frame(latest_frame)
                elif cam_id == 'B':
                    self.update_cctv_b_frame(latest_frame)
                self.frame_buffer[cam_id].clear()

    def setup_marker_overlay(self):
        """마커 오버레이 설정"""
        # 기존 placeholder 제거 및 마커 위젯 추가
        self.map_marker = MapMarkerWidget(self.map_overlay_frame)
        layout = self.map_overlay_frame.layout()
        
        # placeholder 찾기 및 제거
        placeholder_index = layout.indexOf(self.marker_overlay_placeholder)
        if placeholder_index >= 0:
            layout.removeWidget(self.marker_overlay_placeholder)
            self.marker_overlay_placeholder.deleteLater()
        
        # 마커 위젯을 지도와 같은 위치(row 3)에 추가하여 오버레이 효과
        layout.addWidget(self.map_marker, 3, 0)
        
        # 마커 클릭 시그널 연결
        self.map_marker.marker_clicked.connect(self.on_marker_clicked)

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

    def process_pending_updates(self):
        """대기 중인 객체 업데이트 처리"""
        if not self.pending_objects:
            return

        current_time = datetime.now().timestamp()
        # 설정된 조건에 따라 업데이트
        if (current_time - self.last_update_time >= self.settings.data.object_update_min_interval or 
            len(self.pending_objects) >= self.settings.data.object_update_threshold):
            if self.settings.debug.object_update_debug:
                logger.debug(f"객체 업데이트 처리: {len(self.pending_objects)}개 객체")
            self._update_object_list(self.pending_objects)
            self.pending_objects = []
            self.last_update_time = current_time

    def update_object_list(self, objects: list[DetectedObject] | DetectedObject):
        """객체 목록 업데이트 (디바운싱 적용)"""
        # 단일 객체인 경우 리스트로 변환
        if isinstance(objects, DetectedObject):
            objects = [objects]
            
        # 대기 중인 객체 목록에 추가
        self.pending_objects.extend(objects)
        
        # 대기 중인 객체가 너무 많아지면 강제로 업데이트
        if len(self.pending_objects) >= self.settings.data.object_update_force_threshold:
            if self.settings.debug.object_update_debug:
                logger.debug(f"강제 객체 업데이트: {len(self.pending_objects)}개 객체")
            self.process_pending_updates()

    def _update_object_list(self, objects: list[DetectedObject]):
        """실제 객체 목록 업데이트 처리"""
        logger.debug(f"객체 목록 업데이트: {len(objects)}개 객체")
        
        # 중복 제거: 이미 처리된 객체는 제외
        new_objects = [obj for obj in objects if obj.object_id not in self.current_object_ids]
            
        # 현재 처리된 객체 ID 업데이트
        self.current_object_ids.update(obj.object_id for obj in new_objects)
        
        # 테이블 업데이트
        self.table_object_list.setRowCount(len(self.current_object_ids))
        
        # 모든 객체 정보 업데이트
        for row, obj in enumerate(new_objects):
            # ID
            self.table_object_list.setItem(row, 0, QTableWidgetItem(str(obj.object_id)))
            # 위치
            self.table_object_list.setItem(row, 1, QTableWidgetItem(obj.zone.value))
            # 종류
            self.table_object_list.setItem(row, 2, QTableWidgetItem(obj.object_type.value))

        # 마커 업데이트
        self.update_markers(new_objects)

        # 처리된 객체 ID 목록을 메인 윈도우에 전달
        self.object_list_updated.emit(self.current_object_ids)

        # 첫 객체 감지 시 팝업 표시
        if self.is_first_detection and new_objects:
            self.is_first_detection = False
            logger.info("첫 번째 객체 감지")
            dialog = ObjectDetectionDialog(new_objects[0], self)
            dialog.exec()

    def update_markers(self, objects: list[DetectedObject]):
        """마커 업데이트 - 새로운 마커 시스템 사용"""
        logger.debug(f"마커 업데이트: {len(objects)}개 객체")
        
        if not hasattr(self, 'map_marker'):
            logger.warning("map_marker가 초기화되지 않음")
            return

        # 기존 마커들 중 더 이상 존재하지 않는 객체들 제거
        current_object_ids = {obj.object_id for obj in objects}
        existing_marker_ids = set(self.map_marker.markers.keys())
        
        for marker_id in existing_marker_ids - current_object_ids:
            self.map_marker.remove_marker(marker_id)
            logger.debug(f"마커 제거: ID {marker_id}")

        # 새로운 객체들 또는 업데이트된 객체들 처리
        for obj in objects:
            marker_data = self.create_marker_data_from_object(obj)
            
            if obj.object_id in existing_marker_ids:
                # 기존 마커 업데이트
                self.map_marker.update_marker(marker_data)
            else:
                # 새 마커 추가
                self.map_marker.add_dynamic_marker(marker_data)
                logger.debug(f"마커 추가: ID {obj.object_id}")

    def create_marker_data_from_object(self, obj: DetectedObject) -> MarkerData:
        """DetectedObject를 MarkerData로 변환"""
        # 객체 타입을 마커 타입으로 매핑
        object_type_to_marker_type = {
            ObjectType.BIRD: MarkerType.BIRD,
            ObjectType.AIRPLANE: MarkerType.AIRCRAFT,
            ObjectType.VEHICLE: MarkerType.VEHICLE,
            ObjectType.FOD: MarkerType.DEBRIS,
            ObjectType.PERSON: MarkerType.PERSON,
            ObjectType.ANIMAL: MarkerType.ANIMAL,
            ObjectType.FIRE: MarkerType.FIRE,
            ObjectType.WORK_PERSON: MarkerType.WORK_PERSON,
            ObjectType.WORK_VEHICLE: MarkerType.WORK_VEHICLE
        }
        
        # 기본 마커 상태 설정
        marker_state = MarkerState.NORMAL
        
        # 위험도에 따른 마커 상태 설정
        if obj.risk_level is not None:
            if obj.risk_level == BirdRiskLevel.HIGH:
                marker_state = MarkerState.DANGER
            elif obj.risk_level == BirdRiskLevel.MEDIUM:
                marker_state = MarkerState.WARNING
            elif obj.risk_level == BirdRiskLevel.LOW:
                marker_state = MarkerState.NORMAL
        
        # 좌표 정규화 (예: 0~100 범위를 0.0~1.0으로)
        # 실제 좌표 시스템에 맞게 조정 필요
        normalized_x = obj.x_coord / 100.0 if hasattr(obj, 'x_coord') else 0.5
        normalized_y = obj.y_coord / 100.0 if hasattr(obj, 'y_coord') else 0.5
        
        # 범위 제한
        normalized_x = max(0.0, min(1.0, normalized_x))
        normalized_y = max(0.0, min(1.0, normalized_y))
        
        return MarkerData(
            marker_id=obj.object_id,
            x=normalized_x,
            y=normalized_y,
            marker_type=object_type_to_marker_type.get(obj.object_type, MarkerType.UNKNOWN),
            state=marker_state,
            label=str(obj.object_id),
            icon_path=self.marker_icon_path if os.path.exists(self.marker_icon_path) else None,
            size=32 if marker_state in [MarkerState.WARNING, MarkerState.DANGER] else 24
        )

    def on_marker_clicked(self, marker_id: int):
        """마커 클릭 처리"""
        logger.debug(f"마커 클릭: ID {marker_id}")
        
        # 마커 선택 상태 업데이트
        self.map_marker.select_marker(marker_id)
        
        # 테이블에서 해당 행 선택
        self.select_table_row_by_id(marker_id)

    def select_table_row_by_id(self, object_id: int):
        """객체 ID로 테이블 행 선택"""
        for row in range(self.table_object_list.rowCount()):
            item = self.table_object_list.item(row, 0)
            if item and int(item.text()) == object_id:
                self.table_object_list.selectRow(row)
                logger.debug(f"테이블 행 선택: {row} (ID: {object_id})")
                break

    def update_bird_risk(self, risk_level: BirdRiskLevel):
        """조류 위험도 업데이트"""
        logger.info(f"조류 위험도 변경: {risk_level.value}")
        self.label_bird_risk_status.setText(risk_level.value)
        self.label_bird_risk_status.setStyleSheet(
            f"background-color: {Constants.Display.RISK_COLORS[risk_level]}; "
            f"color: {'#000000' if risk_level == BirdRiskLevel.MEDIUM else '#FFFFFF'}; "
            "font-weight: bold;"
        )

    def update_runway_a_risk(self, risk_level: RunwayRiskLevel):
        """활주로 A 위험도 업데이트"""
        logger.info(f"활주로 A 위험도 변경: {risk_level.value}")
        self.label_rwy1_status.setText(risk_level.value)
        self.label_rwy1_status.setStyleSheet(
            f"background-color: {Constants.Display.RISK_COLORS[risk_level]}; "
            f"color: {'#000000' if risk_level == RunwayRiskLevel.MEDIUM else '#FFFFFF'}; "
            "font-weight: bold;"
        )

    def update_runway_b_risk(self, risk_level: RunwayRiskLevel):
        """활주로 B 위험도 업데이트"""
        logger.info(f"활주로 B 위험도 변경: {risk_level.value}")
        self.label_rwy2_status.setText(risk_level.value)
        self.label_rwy2_status.setStyleSheet(
            f"background-color: {Constants.Display.RISK_COLORS[risk_level]}; "
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
        """창 크기 변경 시 이미지 업데이트"""
        super().resizeEvent(event)
        self.update_map_image()

    def update_map_image(self):
        """지도 이미지 업데이트"""
        if not self.map_pixmap.isNull():
            # label_map의 현재 크기 가져오기
            label_size = self.label_map.size()
            logger.debug(f"label_map 크기: {label_size.width()}x{label_size.height()}")
            
            # 이미지 스케일링 및 설정
            scaled_pixmap = self.map_pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.label_map.setPixmap(scaled_pixmap)
            logger.debug(f"지도 이미지 업데이트 완료: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
        else:
            logger.warning("지도 이미지가 null임")

    def select_table_row(self, row_idx):
        """테이블 행 선택 (기존 메서드 유지)"""
        logger.debug(f"테이블 행 선택: {row_idx}")
        self.table_object_list.selectRow(row_idx)

    def show_map(self):
        """지도 보기"""
        logger.info("지도 보기")
        self.map_cctv_stack.setCurrentIndex(0)
        
        # 서버에 지도 요청
        if hasattr(self, 'network_manager'):
            self.network_manager.request_map()
        
        # 지도 표시 시 이미지 다시 업데이트
        QTimer.singleShot(100, self.update_map_image)

    def show_cctv(self):
        """CCTV 보기"""
        idx = self.combo_cctv.currentIndex()
        logger.info(f"CCTV 보기: {idx + 1}")
        self.map_cctv_stack.setCurrentIndex(idx + 1)
        if idx == 0:
            self.network_manager.request_cctv_a()
        elif idx == 1:
            self.network_manager.request_cctv_b()

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
        self.network_manager.request_object_detail(object_id)

    def update_cctv_a_frame(self, frame: QImage):
        """CCTV A 프레임 업데이트"""
        try:
            if frame.isNull():
                return
                
            # 라벨 크기에 맞게 이미지 크기 조정
            scaled_pixmap = QPixmap.fromImage(frame).scaled(
                self.label_cctv_1.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 이미지 표시
            self.label_cctv_1.setPixmap(scaled_pixmap)
            self.label_cctv_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 프레임 업데이트 강제
            self.label_cctv_1.repaint()
            
        except Exception as e:
            logger.error(f"CCTV A 프레임 업데이트 오류: {str(e)}")

    def update_cctv_b_frame(self, frame: QImage):
        """CCTV B 프레임 업데이트"""
        try:
            if frame.isNull():
                return
                
            # 라벨 크기에 맞게 이미지 크기 조정
            scaled_pixmap = QPixmap.fromImage(frame).scaled(
                self.label_cctv_2.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 이미지 표시
            self.label_cctv_2.setPixmap(scaled_pixmap)
            self.label_cctv_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 프레임 업데이트 강제
            self.label_cctv_2.repaint()
            
        except Exception as e:
            logger.error(f"CCTV B 프레임 업데이트 오류: {str(e)}")

    def closeEvent(self, event):
        """위젯 종료 시 처리"""
        # 네트워크 서비스 중지
        if hasattr(self, 'network_manager'):
            self.network_manager.stop_services()

        # UDP 클라이언트 정리
        if hasattr(self, 'udp_client'):
            self.udp_client.cleanup()

        # 마커 정리
        if hasattr(self, 'map_marker'):
            self.map_marker.clear_markers()
        
        super().closeEvent(event)