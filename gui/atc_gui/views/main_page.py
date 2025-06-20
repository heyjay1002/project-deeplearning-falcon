from PyQt6.QtWidgets import *
from PyQt6 import uic
from PyQt6.QtGui import QPixmap, QColor, QImage, QPainter, QPen
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime
import sys
import os

# 상위 디렉토리를 파이썬 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # atc_gui 디렉토리
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from views.object_detail_dialog import ObjectDetailDialog
from config.constants import BirdRiskLevel, RunwayRiskLevel, ObjectType, AirportZone
from config.settings import Settings
from utils.network_manager import NetworkManager
from utils.udp_client import UdpClient
from utils.interface import DetectedObject, BirdRisk, RunwayRisk
from utils.logger import logger
from widgets.map_marker_widget import MapMarkerWidget
import time
from collections import deque
import cv2
from typing import Optional

class MainPage(QWidget):
    # 객체 목록 업데이트 시그널 추가
    object_list_updated = pyqtSignal(set)   
    object_detected = pyqtSignal(DetectedObject)
    bird_risk_alerted = pyqtSignal(BirdRisk)
    runway_risk_alerted = pyqtSignal(RunwayRisk)

    def __init__(self, parent=None, network_manager=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), '../ui/main_page.ui')
        uic.loadUi(ui_path, self)

        # 현재 처리된 객체 ID 저장
        self.current_object_ids = set()

        # 설정 로드
        self.settings = Settings.get_instance()

        # 프레임 버퍼 및 디스플레이 타이머 초기화
        self.frame_buffer = {'A': deque(maxlen=5), 'B': deque(maxlen=5)}
        self.target_fps = 30  # FPS를 30으로 증가
        self.frame_display_timer = QTimer(self)
        self.frame_display_timer.timeout.connect(self.display_latest_frames)
        self.frame_display_timer.start(int(1000 / self.target_fps))  # 약 33ms 간격
        logger.info(f"프레임 디스플레이 타이머 시작됨 (FPS: {self.target_fps}, 간격: {int(1000 / self.target_fps)}ms)")
        
        # 마지막으로 표시한 이미지ID 저장
        self.last_displayed_image_id = {'A': -1, 'B': -1}

        # 테이블 설정
        self.setup_table()
        
        # 네트워크 관리자 설정
        self.network_manager = network_manager
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

        # 초기 조류 위험도 설정
        self.update_bird_risk(None)  # 기본값(안전)으로 설정

        # 초기 활주로 위험도 설정
        self.update_runway_a_risk(None)
        self.update_runway_b_risk(None)

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

        # 테이블 클릭 시 마커 선택 효과 적용
        self.table_object_list.cellClicked.connect(self.on_table_object_clicked)

    def on_table_object_clicked(self, row, column):
        """테이블에서 객체 클릭 시 마커 선택 효과 적용"""
        item = self.table_object_list.item(row, 0)  # 0번 컬럼: object_id
        if item is not None:
            object_id = int(item.text())
            self.map_marker.select_marker(object_id)
            logger.debug(f"테이블 클릭: ID {object_id}")

    def setup_network_manager(self):
        """네트워크 관리자 시그널만 연결, 서비스 시작/중지는 WindowClass에서 관리"""
        if self.network_manager is None:
            raise ValueError("network_manager가 필요합니다.")
        # 시그널 연결만 수행
        self.network_manager.object_detected.connect(self.update_object_list)
        self.network_manager.bird_risk_changed.connect(self.update_bird_risk)
        self.network_manager.runway_a_risk_changed.connect(self.update_runway_a_risk)
        self.network_manager.runway_b_risk_changed.connect(self.update_runway_b_risk)
        self.network_manager.object_detail_response.connect(self.update_object_detail)
        self.network_manager.object_detail_error.connect(self.handle_object_detail_error)
        # CCTV 프레임은 UDP 클라이언트에서 직접 처리하므로 NetworkManager 시그널 연결 제거
        # self.network_manager.frame_a_received.connect(self.update_cctv_a_frame)
        # self.network_manager.frame_b_received.connect(self.update_cctv_b_frame)
        self.network_manager.tcp_connection_status_changed.connect(self.update_tcp_connection_status)
        self.network_manager.udp_connection_status_changed.connect(self.update_udp_connection_status)
        # 서비스 시작/중지는 WindowClass에서만!

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
        """TCP 연결 상태 UI 업데이트"""
        logger.info(f"TCP 연결 상태 변경: {message}")
        if hasattr(self, 'tcp_status_label'):
            if is_connected:
                self.tcp_status_label.setStyleSheet("color: green; font-weight: bold; margin-right: 8px;")
            else:
                self.tcp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")

    def update_udp_connection_status(self, is_connected: bool, message: str):
        """UDP 연결 상태 UI 업데이트"""
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

    def handle_udp_frame(self, cam_id: str, frame, image_id: int = None):
        """UDP로 수신된 프레임 처리"""
        try:            
            logger.info(f"UDP 프레임 수신: 카메라={cam_id}, 이미지ID={image_id}")
            self.last_displayed_image_id[cam_id] = image_id
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            if q_image.isNull():
                logger.warning(f"CCTV {cam_id} QImage 변환 실패")
                return
                
            # 이미지ID와 함께 저장
            self.frame_buffer[cam_id].append((image_id, q_image))
            logger.info(f"CCTV {cam_id} 프레임 버퍼에 저장됨 (총 {len(self.frame_buffer[cam_id])}개)")
            
        except Exception as e:
            logger.error(f"UDP 프레임 처리 오류: {str(e)}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")

    def display_latest_frames(self):
        """가장 최신 프레임 표시"""
        logger.info("프레임 디스플레이 타이머 실행")
        total_frames = 0
        for cam_id in ['A', 'B']:
            if self.frame_buffer[cam_id]:
                # 가장 최신 프레임만 꺼내서 디스플레이
                _, latest_frame = self.frame_buffer[cam_id][-1]
                logger.info(f"CCTV {cam_id} 프레임 표시 중 (버퍼 크기: {len(self.frame_buffer[cam_id])})")
                if cam_id == 'A':
                    self.update_cctv_a_frame(latest_frame)
                elif cam_id == 'B':
                    self.update_cctv_b_frame(latest_frame)
                self.frame_buffer[cam_id].clear()
                total_frames += 1
            else:
                logger.debug(f"CCTV {cam_id} 프레임 버퍼가 비어있음")
        
        if total_frames > 0:
            logger.debug(f"총 {total_frames}개 프레임 표시 완료")

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
        """객체 목록 업데이트"""
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

        # 첫 객체 감지 시 시그널로 전달
        if self.is_first_detection and new_objects:
            self.is_first_detection = False
            logger.info("첫 번째 객체 감지")
            self.object_detected.emit(new_objects[0])  # 시그널로만 전달

    def update_markers(self, objects: list[DetectedObject]):
        """마커 업데이트"""
        logger.debug(f"마커 업데이트: {len(objects)}개 객체")
        
        if not hasattr(self, 'map_marker'):
            logger.warning("map_marker가 초기화되지 않음")
            return

        # 현재 객체 ID 목록
        current_object_ids = {obj.object_id for obj in objects}
        
        # 더 이상 존재하지 않는 객체의 마커 제거
        existing_object_ids = set(self.map_marker.markers.keys())
        for object_id in existing_object_ids - current_object_ids:
            self.map_marker.remove_marker(object_id)
            logger.debug(f"마커 제거: ID {object_id}")

        # 새로운 객체들 또는 업데이트된 객체들 처리
        for obj in objects:
            try:
                # 마커 데이터 생성
                marker_data = self.map_marker.create_marker_data(obj)
                
                if obj.object_id in existing_object_ids:
                    # 기존 마커 업데이트
                    self.map_marker.update_marker(marker_data)
                    logger.debug(f"마커 업데이트: ID {obj.object_id}")
                else:
                    # 새 마커 추가
                    self.map_marker.add_dynamic_marker(marker_data)
                    logger.debug(f"마커 추가: ID {obj.object_id}")
                    
            except Exception as e:
                logger.error(f"마커 처리 중 오류 발생 (ID: {obj.object_id}): {str(e)}")
                continue    

    def on_marker_clicked(self, object_id: int):
        """마커 클릭 처리"""
        logger.debug(f"마커 클릭: ID {object_id}")
        
        # 마커 선택 상태 업데이트
        self.map_marker.select_marker(object_id)
        
        # 테이블에서 해당 행 선택
        self.select_table_row_by_id(object_id)

    def select_table_row_by_id(self, object_id: int):
        """객체 ID로 테이블 행 선택"""
        for row in range(self.table_object_list.rowCount()):
            item = self.table_object_list.item(row, 0)
            if item and int(item.text()) == object_id:
                self.table_object_list.selectRow(row)
                logger.debug(f"테이블 행 선택: {row} (ID: {object_id})")
                break

    def update_bird_risk(self, risk_level: Optional[BirdRiskLevel] = None):
        """조류 위험도 업데이트"""
        # risk_level이 None이면 기본값으로 LOW(안전) 설정
        if risk_level is None:
            risk_level = BirdRiskLevel.LOW
            logger.info("조류 위험도 값이 없어 기본값(안전)으로 설정됨")
        else:
            logger.info(f"조류 위험도 변경: {risk_level.value}")
            
        self.label_bird_risk_status.setText(risk_level.value)
        
        # 위험도에 따른 스타일 설정
        if risk_level == BirdRiskLevel.LOW:  # 안전 (0)
            self.label_bird_risk_status.setStyleSheet(
                "background-color: #00FF00; "  # 녹색
                "color: #000000; "
                "font-weight: bold; "
                "border: 1px solid #008000; "  # 진한 녹색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
        elif risk_level == BirdRiskLevel.MEDIUM:  # 주의 (1)
            self.label_bird_risk_status.setStyleSheet(
                "background-color: #FFFF00; "  # 노란색
                "color: #000000; "
                "font-weight: bold; "
                "border: 1px solid #FFA500; "  # 주황색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
        else:  # 경고 (2)
            self.label_bird_risk_status.setStyleSheet(
                "background-color: #FF0000; "  # 빨간색
                "color: #FFFFFF; "
                "font-weight: bold; "
                "border: 1px solid #8B0000; "  # 진한 빨간색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
            
        # 위험도 변경 시 시그널로 전달
        if risk_level != BirdRiskLevel.LOW:
            self.bird_risk_alerted.emit(BirdRisk(risk_level))

    def update_runway_a_risk(self, risk_level: Optional[RunwayRiskLevel] = None):
        """활주로 A 위험도 업데이트"""
        # risk_level이 None이면 기본값으로 LOW(안전) 설정
        if risk_level is None:
            risk_level = RunwayRiskLevel.LOW
            logger.info("활주로 A 위험도 값이 없어 기본값(안전)으로 설정됨")
        else:
            logger.info(f"활주로 A 위험도 변경: {risk_level.value}")

        self.label_rwy_a_status.setText(risk_level.value)
        if risk_level == RunwayRiskLevel.LOW:
            self.label_rwy_a_status.setStyleSheet(
                    "background-color: #00FF00; "  # 녹색
                    "color: #000000; "
                    "font-weight: bold; "
                    "border: 1px solid #008000; "  # 진한 녹색 테두리
                    "border-radius: 5px; "
                    "padding: 5px;"
            )
        else:
            self.label_rwy_a_status.setStyleSheet(
                "background-color: #FF0000; "  # 빨간색
                "color: #FFFFFF; "
                "font-weight: bold; "
                "border: 1px solid #8B0000; "  # 진한 빨간색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
            
        # 위험도 변경 시 시그널로 전달
        if risk_level != RunwayRiskLevel.LOW:
            self.runway_risk_alerted.emit(RunwayRisk('A', risk_level))

    def update_runway_b_risk(self, risk_level: Optional[RunwayRiskLevel] = None):
        """활주로 B 위험도 업데이트"""
        # risk_level이 None이면 기본값으로 LOW(안전) 설정
        if risk_level is None:
            risk_level = RunwayRiskLevel.LOW
            logger.info("활주로 B 위험도 값이 없어 기본값(안전)으로 설정됨")
        else:
            logger.info(f"활주로 B 위험도 변경: {risk_level.value}")

        self.label_rwy_b_status.setText(risk_level.value)
        if risk_level == RunwayRiskLevel.LOW:
            self.label_rwy_b_status.setStyleSheet(
                "background-color: #00FF00; "  # 녹색
                "color: #000000; "
                "font-weight: bold; "
                "border: 1px solid #008000; "  # 진한 녹색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
        else:
            self.label_rwy_b_status.setStyleSheet(
                "background-color: #FF0000; "  # 빨간색
                "color: #FFFFFF; "
                "font-weight: bold; "
                "border: 1px solid #8B0000; "  # 진한 빨간색 테두리
                "border-radius: 5px; "
                "padding: 5px;"
            )
            
        # 위험도 변경 시 시그널로 전달
        if risk_level != RunwayRiskLevel.LOW:
            self.runway_risk_alerted.emit(RunwayRisk('B', risk_level))

    def update_object_detail(self, obj: DetectedObject):
        """객체 상세 정보 업데이트"""
        logger.info(f"객체 상세 정보 수신 완료. ID: {obj.object_id}. 상세 보기로 전환합니다.")
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
        else:
            # 이미지가 없을 경우, 회색 배경에 텍스트가 있는 플레이스홀더 생성
            img_label = self.object_detail_dialog.detail_img
            pixmap = QPixmap(img_label.size())
            pixmap.fill(QColor('lightgray'))
            
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor('black')))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 없음")
            painter.end()
            
            img_label.setPixmap(pixmap)

        self.object_area.setCurrentIndex(2)

    def handle_object_detail_error(self, error_msg: str):
        """객체 상세보기 오류 처리"""
        logger.error(f"객체 상세보기 오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"객체 상세보기 오류: {error_msg}")

    def select_table_row(self, row_idx):
        """테이블 행 선택 (기존 메서드 유지)"""
        logger.debug(f"테이블 행 선택: {row_idx}")
        self.table_object_list.selectRow(row_idx)

    def show_map(self):
        """지도 보기"""
        logger.info("지도 보기")
        self.map_cctv_stack.setCurrentIndex(0)
        
        # 서버에 지도 요청
        if self.network_manager:
            self.network_manager.request_map()

    def show_cctv(self):
        """CCTV 보기"""
        idx = self.combo_cctv.currentIndex()
        logger.info(f"CCTV 보기: {idx + 1}")
        self.map_cctv_stack.setCurrentIndex(idx + 1)
        
        # 타이머 상태 확인
        if self.frame_display_timer.isActive():
            logger.info(f"프레임 디스플레이 타이머 활성화됨 (간격: {self.frame_display_timer.interval()}ms)")
        else:
            logger.warning("프레임 디스플레이 타이머가 비활성화됨 - 재시작")
            self.frame_display_timer.start(int(1000 / self.target_fps))
        
        # 이전 CCTV 연결 해제
        if hasattr(self, 'udp_client'):
            self.udp_client.disconnect()
            
        if idx == 0:
            logger.info("CCTV A 선택됨 - 요청 전송")
            self.network_manager.request_cctv_a()
            # UDP 연결 시도
            logger.info(f"CCTV A UDP 연결 시도: {self.settings.server.udp_ip}:{self.settings.server.udp_port}")
            if not self.udp_client.connect(self.settings.server.udp_ip, self.settings.server.udp_port):
                self.update_udp_connection_status(False, "CCTV A 연결 실패")
                logger.error("CCTV A UDP 연결 실패")
            else:
                logger.info("CCTV A UDP 연결 성공")
                
            # 테스트용 더미 프레임 생성 (서버에서 프레임이 오지 않을 경우)
            self.create_test_frame()
        elif idx == 1:
            logger.info("CCTV B 선택됨 - 요청 전송")
            self.network_manager.request_cctv_b()
            # UDP 연결 시도
            if not self.udp_client.connect(self.settings.server.udp_ip, self.settings.server.udp_port):
                self.update_udp_connection_status(False, "CCTV B 연결 실패")
                logger.error("CCTV B UDP 연결 실패")

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
        logger.info(f"객체 상세보기 요청 시작: ID {object_id}")
        self.network_manager.request_object_detail(object_id)

    def update_cctv_a_frame(self, frame: QImage):
        """CCTV A 프레임 업데이트"""
        try:
            logger.debug(f"CCTV A 프레임 업데이트 시작 - 프레임 크기: {frame.size() if not frame.isNull() else 'Null'}")
            if frame.isNull():
                logger.warning("CCTV A 프레임이 Null입니다")
                return
                
            # 라벨 크기에 맞게 이미지 크기 조정
            label_size = self.label_cctv_1.size()
            logger.debug(f"CCTV A 라벨 크기: {label_size}")
            
            scaled_pixmap = QPixmap.fromImage(frame).scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            logger.debug(f"CCTV A 스케일된 이미지 크기: {scaled_pixmap.size()}")
            
            # 이미지 표시
            self.label_cctv_1.setPixmap(scaled_pixmap)
            self.label_cctv_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 프레임 업데이트 강제
            self.label_cctv_1.repaint()
            logger.info("CCTV A 프레임 업데이트 완료 - 화면에 표시됨")
            
        except Exception as e:
            logger.error(f"CCTV A 프레임 업데이트 오류: {str(e)}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")

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
        # UDP 클라이언트 정리
        if hasattr(self, 'udp_client'):
            self.udp_client.cleanup()

        # 마커 정리
        if hasattr(self, 'map_marker'):
            self.map_marker.clear_markers()
        
        super().closeEvent(event)