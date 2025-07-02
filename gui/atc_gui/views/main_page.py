from PyQt6 import uic
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget, QLabel, QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime
import os
from views.object_detail_dialog import ObjectDetailDialog
from config.constants import BirdRiskLevel, RunwayRiskLevel
from config.settings import Settings
from utils.interface import DetectedObject, BirdRisk, RunwayRisk, ObjectType, AirportArea, EventType
from utils.logger import logger
from widgets.map_marker_widget import MapMarkerWidget
from typing import Optional
import time

class MainPage(QWidget):
    # 객체 목록 업데이트 시그널 추가
    object_list_updated = pyqtSignal(set)
    bird_risk_alerted = pyqtSignal(BirdRisk)
    runway_risk_alerted = pyqtSignal(RunwayRisk)

    def __init__(self, parent=None, network_manager=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), '../ui/main_page.ui')
        uic.loadUi(ui_path, self)

        # 현재 처리된 객체 ID 저장
        self.current_object_ids = set()
        self.first_detected_object_ids = set() # 최초 감지 알림 중복 방지용
        
        # 객체 마지막 업데이트 시간 추적 (타임아웃용)
        self.object_last_seen = {}  # {object_id: timestamp}
        self.object_timeout_seconds = 2.0  # 2초 동안 업데이트 없으면 제거
        
        # FPS 추적을 위한 변수들
        self.cctv_a_fps = 0
        self.cctv_b_fps = 0
        self.cctv_a_frame_count = 0
        self.cctv_b_frame_count = 0
        self.cctv_a_last_time = 0
        self.cctv_b_last_time = 0
        
        # 설정 로드
        self.settings = Settings.get_instance()

        # 테이블 설정
        self.setup_table()
        
        # 네트워크 관리자 설정
        self.network_manager = network_manager
        self.setup_network_manager()

        # 마커 오버레이 연동
        self.setup_marker_overlay()

        # 버튼 연결
        self.setup_buttons()

        # 상세보기 다이얼로그 설정
        self.setup_detail_dialog()

        # 객체 업데이트 최적화를 위한 변수들
        self.pending_objects = []  # 대기 중인 객체 목록
        self.last_update_time = 0  # 마지막 업데이트 시간
        self.update_timer = QTimer(self)  # 업데이트 타이머
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.update_timer.start(self.settings.data.object_update_interval)

        # 객체 타임아웃 체크 타이머
        self.timeout_timer = QTimer(self)
        self.timeout_timer.timeout.connect(self.check_object_timeouts)
        self.timeout_timer.start(1000)

        # 현재 시간 업데이트 설정
        self.setup_current_time()

        # 스택 위젯 초기 상태 설정
        self.map_cctv_stack.setCurrentIndex(0)

        # 초기 조류/활주로 위험도 설정
        self.update_bird_risk(None)
        self.update_runway_a_risk(None)
        self.update_runway_b_risk(None)

    def setup_table(self):
        """테이블 초기 설정"""
        headers = ["ID", "종류", "위치"]
        self.table_object_list.setColumnCount(len(headers))
        self.table_object_list.setHorizontalHeaderLabels(headers)
        self.table_object_list.setSelectionBehavior(self.table_object_list.SelectionBehavior.SelectRows)
        self.table_object_list.horizontalHeader().setStretchLastSection(True)
        self.table_object_list.horizontalHeader().setSectionResizeMode(0, self.table_object_list.horizontalHeader().ResizeMode.ResizeToContents)
        self.table_object_list.horizontalHeader().setSectionResizeMode(1, self.table_object_list.horizontalHeader().ResizeMode.Stretch)
        self.table_object_list.horizontalHeader().setSectionResizeMode(2, self.table_object_list.horizontalHeader().ResizeMode.Stretch)
        self.table_object_list.setRowCount(0)
        self.table_object_list.cellClicked.connect(self.on_table_object_clicked)
        
        # LogPage와 동일한 테이블 스타일 적용
        self.apply_table_style()

    def apply_table_style(self):
        """테이블 스타일 적용 (LogPage와 동일)"""
        try:
            table = self.table_object_list
            
            table_style = """
                QTableWidget {
                    gridline-color: #e0e0e0;
                    background-color: #ffffff;
                    alternate-background-color: #f8f9fa;
                    selection-background-color: #007acc;
                    selection-color: white;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                }                
                QHeaderView::section {
                    background-color: #f6f8fa;
                    padding: 10px;
                    border: none;
                    border-bottom: 2px solid #e1e4e8;
                    border-right: 1px solid #e1e4e8;
                    font-weight: bold;
                    color: #24292f;
                    text-align: center;
                }
                QHeaderView::section:hover {
                    background-color: #eaeef2;
                }
                QScrollBar:vertical {
                    background: #f6f8fa;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background: #d0d7de;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #656d76;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
                QScrollBar:horizontal {
                    background: #f6f8fa;
                    height: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:horizontal {
                    background: #d0d7de;
                    border-radius: 6px;
                    min-width: 20px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #656d76;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
            """
            table.setStyleSheet(table_style)
            
            # 폰트 크기 설정
            font = table.font()
            font.setPointSize(12)
            table.setFont(font)
            
            # 행 높이 설정
            table.verticalHeader().setDefaultSectionSize(40)
            
            # 테이블 속성 설정
            table.setAlternatingRowColors(True)  # 행 색상 교대로 표시
            table.setShowGrid(True)
            table.verticalHeader().setVisible(False)  # 행 번호 숨기기
            
        except Exception as e:
            logger.error(f"테이블 스타일 적용 오류: {e}")

    def on_table_object_clicked(self, row, column):
        """테이블에서 객체 클릭 시 마커 선택 효과만 적용"""
        item = self.table_object_list.item(row, 0)
        if item is not None:
            object_id = int(item.text())
            logger.info(f"테이블 행 클릭: ID {object_id}")
            
            # 마커 선택만 수행
            self.map_marker.select_marker(object_id)
            logger.info(f"마커 선택 완료: ID {object_id}")

    def setup_network_manager(self):
        """네트워크 관리자 시그널만 연결"""
        if self.network_manager is None:
            raise ValueError("network_manager가 필요합니다.")
        
        # [수정] first_object_detected 신호 연결 추가
        self.network_manager.first_object_detected.connect(self.on_first_object_detected)
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
        
        self.network_manager.tcp_client.cctv_a_response.connect(self.on_cctv_a_response)
        self.network_manager.tcp_client.cctv_b_response.connect(self.on_cctv_b_response)

    def on_first_object_detected(self, obj: DetectedObject):
        """최초 감지 객체(ME_FD)를 처리하여 알림을 발생시킵니다."""
        logger.info(f"MainPage: 최초 감지 이벤트 수신 - ID {obj.object_id}, Type {obj.object_type.value}, Area {obj.area.value}")
        
        # RESCUE 이벤트에서 PERSON/WORK_PERSON 객체의 위험도 1인 경우 특별 알림
        if (obj.event_type and obj.event_type.value == "구조" and 
            obj.object_type in [ObjectType.PERSON, ObjectType.WORK_PERSON] and 
            obj.state_info == 1):
            
            logger.warning(f"🚨 구조 요청 알림: ID {obj.object_id}, Type {obj.object_type.value}, 위험도 {obj.state_info}")
            
            # 부모 윈도우(메인 윈도우)의 알림 다이얼로그 직접 호출
            main_window = self.window()
            if hasattr(main_window, 'show_notification_dialog'):
                main_window.show_notification_dialog('rescue', obj)
                logger.info(f"MainPage: 구조 요청 알림 발생: ID {obj.object_id} ({obj.object_type.value}) - 위험도 {obj.state_info}")
            else:
                logger.error("MainPage: main_window에 show_notification_dialog 메서드가 없습니다")
            
            return  # 구조 요청 알림이 발생했으므로 일반 알림은 발생시키지 않음
        
        # 출입등급 변경으로 인한 새로운 위험요소 감지인지 확인
        # 기존에 감지된 객체라도 출입등급 변경으로 위험요소가 된 경우 알림 발생
        if obj.object_id not in self.first_detected_object_ids:
            self.first_detected_object_ids.add(obj.object_id)
            logger.info(f"MainPage: 새로운 객체 최초 감지 - ID {obj.object_id}를 first_detected_object_ids에 추가")
            
            # 부모 윈도우(메인 윈도우)의 알림 다이얼로그 직접 호출
            main_window = self.window()
            if hasattr(main_window, 'show_notification_dialog'):
                main_window.show_notification_dialog('object', obj)
                logger.info(f"MainPage: 최초 감지(ME_FD) 알림 발생: ID {obj.object_id} ({obj.object_type.value})")
            else:
                logger.error("MainPage: main_window에 show_notification_dialog 메서드가 없습니다")
        else:
            # 기존 객체 ID가 있지만 출입등급 변경으로 인한 새로운 위험요소인 경우
            # 이 경우에도 알림을 발생시킴 (출입등급 변경 후 위험요소로 인식되는 경우)
            logger.info(f"MainPage: 기존 객체 ID {obj.object_id}가 출입등급 변경으로 인한 새로운 위험요소로 감지됨")
            main_window = self.window()
            if hasattr(main_window, 'show_notification_dialog'):
                main_window.show_notification_dialog('object', obj)
                logger.info(f"MainPage: 출입등급 변경 후 위험요소 감지 알림 발생: ID {obj.object_id} ({obj.object_type.value})")
            else:
                logger.error("MainPage: main_window에 show_notification_dialog 메서드가 없습니다")

    def on_cctv_a_response(self, response: str):
        """CCTV A 응답 처리"""
        if response == "OK":
            self.map_cctv_stack.setCurrentIndex(1)
            self.cctv_a_frame_count = 0
            self.cctv_a_last_time = 0
            self.cctv_a_fps = 0
            self.label_cctv_1.setText("CCTV A 연결 중...\nUDP 프레임 수신 대기")
            self.label_cctv_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_cctv_1.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        else:
            self.label_cctv_1.setText(f"CCTV A 연결 실패\n{response}")
            self.label_cctv_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_cctv_1.setStyleSheet("background-color: #ffebee; border: 1px solid #f44336; color: #d32f2f;")

    def on_cctv_b_response(self, response: str):
        """CCTV B 응답 처리"""
        if response == "OK":
            self.map_cctv_stack.setCurrentIndex(1)
            self.cctv_b_frame_count = 0
            self.cctv_b_last_time = 0
            self.cctv_b_fps = 0
            self.label_cctv_2.setText("CCTV B 연결 중...\nUDP 프레임 수신 대기")
            self.label_cctv_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_cctv_2.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        else:
            self.label_cctv_2.setText(f"CCTV B 연결 실패\n{response}")
            self.label_cctv_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_cctv_2.setStyleSheet("background-color: #ffebee; border: 1px solid #f44336; color: #d32f2f;")

    def setup_status_bar(self):
        """커스텀 상태바 위젯 설정 (TCP/UDP 상태만)"""
        main_window = self.window()
        if hasattr(main_window, 'statusBar'):
            status_bar = main_window.statusBar()
            if not hasattr(self, 'tcp_status_label'):
                self.tcp_status_label = QLabel("TCP ●")
                self.udp_status_label = QLabel("UDP ●")
                self.tcp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")
                self.udp_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 8px;")
                status_bar.addWidget(self.tcp_status_label)
                status_bar.addWidget(self.udp_status_label)

    def update_tcp_connection_status(self, is_connected: bool, message: str):
        """TCP 연결 상태 UI 업데이트"""
        if hasattr(self, 'tcp_status_label'):
            color = "green" if is_connected else "red"
            self.tcp_status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 8px;")

    def update_udp_connection_status(self, is_connected: bool, message: str):
        """UDP 연결 상태 UI 업데이트"""
        if hasattr(self, 'udp_status_label'):
            color = "green" if is_connected else "red"
            self.udp_status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 8px;")

    def setup_marker_overlay(self):
        """마커 오버레이 설정"""
        self.map_marker = MapMarkerWidget(self.map_overlay_frame)
        layout = self.map_overlay_frame.layout()
        placeholder_index = layout.indexOf(self.marker_overlay_placeholder)
        if placeholder_index >= 0:
            layout.removeWidget(self.marker_overlay_placeholder)
            self.marker_overlay_placeholder.deleteLater()
        layout.addWidget(self.map_marker, 3, 0)
        self.map_marker.marker_clicked.connect(self.on_marker_clicked)

    def setup_buttons(self):
        """버튼 시그널 연결 및 스타일 설정"""
        self.btn_show_map.clicked.connect(self.show_map)
        self.btn_show_cctv.clicked.connect(self.show_cctv)
        self.btn_detail.clicked.connect(self.show_detail)

        self.btn_show_map.setStyleSheet("""
            QPushButton {
                    background-color: #17a2b8;
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    font-size: 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
                QPushButton:pressed {
                    background-color: #11707f;
                }
        """)

        self.btn_show_cctv.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                border: none;
                color: white;
                padding: 8px 16px;
                font-size: 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #11707f;
            }
        """)
        
        # 상세보기 버튼 스타일 설정
        self.btn_detail.setStyleSheet("""
            QPushButton {
                background-color: #484848;
                border: none;
                color: white;
                padding: 8px 16px;
                font-size: 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5c5c5c;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

    def setup_detail_dialog(self):
        """상세보기 다이얼로그 설정"""
        self.object_detail_dialog = ObjectDetailDialog(self)
        self.object_area.addWidget(self.object_detail_dialog)
        self.object_detail_dialog.btn_back.clicked.connect(self.show_table)

    def setup_current_time(self):
        """현재 시간 업데이트 설정"""
        # 현재 시간 업데이트 타이머 설정
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(self.update_current_time)
        self.time_update_timer.start(1000)  # 1초마다 업데이트
        
        # 초기 시간 설정
        self.update_current_time()

    def update_current_time(self):
        """현재 시간 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.label_current_time.setText(f"현재 시간: {current_time}")

    def process_pending_updates(self):
        """대기 중인 객체 업데이트 처리"""
        if not self.pending_objects:
            return

        current_time = datetime.now().timestamp()
        if (current_time - self.last_update_time >= self.settings.data.object_update_min_interval or 
            len(self.pending_objects) >= self.settings.data.object_update_threshold):
            if self.settings.debug.object_update_debug:
                logger.debug(f"객체 업데이트 처리: {len(self.pending_objects)}개 객체")
            self._update_object_list(self.pending_objects)
            self.pending_objects = []
            self.last_update_time = current_time

    def update_object_list(self, objects: list[DetectedObject] | DetectedObject):
        """객체 목록 업데이트"""
        if isinstance(objects, DetectedObject):
            objects = [objects]
        
        existing_pending_ids = {obj.object_id for obj in self.pending_objects}
        new_objects = [obj for obj in objects if obj.object_id not in existing_pending_ids]
        
        self.pending_objects.extend(new_objects)
        
        if len(self.pending_objects) >= self.settings.data.object_update_force_threshold:
            if self.settings.debug.object_update_debug:
                logger.debug(f"강제 객체 업데이트: {len(self.pending_objects)}개 객체")
            self.process_pending_updates()

    # [수정] _update_object_list에서 최초 감지 추측 로직 제거
    def _update_object_list(self, objects: list[DetectedObject]):
        """실제 객체 목록 업데이트 처리"""
        logger.debug(f"객체 목록 업데이트: {len(objects)}개 객체")

        current_time = datetime.now().timestamp()
        all_object_ids = {obj.object_id for obj in objects}
        
        for obj in objects:
            self.object_last_seen[obj.object_id] = current_time
        
        disappeared_objects = self.current_object_ids - all_object_ids
        for obj_id in disappeared_objects:
            self.current_object_ids.discard(obj_id)
            self.object_last_seen.pop(obj_id, None)
            logger.debug(f"사라진 객체 ID 제거: {obj_id}")

        # 중복 제거: 이미 처리된 객체는 제외하고 새로운 객체만 찾음
        new_objects = [obj for obj in objects if obj.object_id not in self.current_object_ids]
        logger.debug(f"새로운 객체: {len(new_objects)}개 (전체: {len(objects)}개)")
        
        # 현재 처리된 객체 ID 목록에 새로운 객체 ID 추가
        self.current_object_ids.update(obj.object_id for obj in new_objects)

        # 테이블에서 사라진 row 인덱스 수집 및 삭제
        rows_to_remove = []
        for row in range(self.table_object_list.rowCount()):
            item = self.table_object_list.item(row, 0)
            if item and int(item.text()) not in all_object_ids:
                rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self.table_object_list.removeRow(row)

        # 테이블에 새로운 객체 추가
        for obj in new_objects:
            row_count = self.table_object_list.rowCount()
            self.table_object_list.insertRow(row_count)
            self.table_object_list.setItem(row_count, 0, QTableWidgetItem(str(obj.object_id)))
            self.table_object_list.setItem(row_count, 1, QTableWidgetItem(obj.object_type.value))
            self.table_object_list.setItem(row_count, 2, QTableWidgetItem(obj.area.value))

        # 기존 row 정보 갱신 (위치 등)
        for row in range(self.table_object_list.rowCount()):
            object_id = int(self.table_object_list.item(row, 0).text())
            for obj in objects:
                if obj.object_id == object_id:
                    self.table_object_list.setItem(row, 1, QTableWidgetItem(obj.object_type.value))
                    self.table_object_list.setItem(row, 2, QTableWidgetItem(obj.area.value))
                    break

        # 마커 업데이트: 현재 감지된 모든 객체 기준
        self.update_markers(objects)

        # 처리된 객체 ID 목록을 메인 윈도우에 전달
        self.object_list_updated.emit(self.current_object_ids)
        
        # 사라진 객체들의 최초 감지 기록도 정리
        disappeared_first_ids = self.first_detected_object_ids - self.current_object_ids
        if disappeared_first_ids:
            self.first_detected_object_ids -= disappeared_first_ids
            logger.debug(f"사라진 객체들의 최초 감지 기록 정리: {disappeared_first_ids}")

    def update_markers(self, objects: list[DetectedObject]):
        """마커 업데이트"""
        if not hasattr(self, 'map_marker'):
            logger.warning("map_marker가 초기화되지 않음")
            return

        current_object_ids = {obj.object_id for obj in objects}
        existing_marker_ids = set(self.map_marker.markers.keys())

        # 사라진 마커 제거
        for object_id in existing_marker_ids - current_object_ids:
            self.map_marker.remove_marker(object_id)

        # 새 마커 추가 또는 기존 마커 업데이트
        for obj in objects:
            marker_data = self.map_marker.create_marker_data(obj)
            if obj.object_id in existing_marker_ids:
                self.map_marker.update_marker(marker_data)
            else:
                self.map_marker.add_dynamic_marker(marker_data)

    def on_marker_clicked(self, object_id: int):
        """마커 클릭 처리"""
        logger.info(f"=== MainPage 마커 클릭 처리 시작 ===")
        logger.info(f"클릭된 마커 ID: {object_id}")
        
        # 마커 선택
        logger.info(f"마커 선택 시작: ID {object_id}")
        self.map_marker.select_marker(object_id)
        logger.info(f"마커 선택 완료: ID {object_id}")
        
        # 테이블 행 선택
        logger.info(f"테이블 행 선택 시작: ID {object_id}")
        self.select_table_row_by_id(object_id)
        logger.info(f"테이블 행 선택 완료: ID {object_id}")
        
        # 상세보기 버튼을 누른 효과 - 객체 상세보기 요청
        logger.info(f"객체 상세보기 요청 시작: ID {object_id}")
        self.network_manager.request_object_detail(object_id)
        logger.info(f"객체 상세보기 요청 완료: ID {object_id}")
        logger.info(f"=== MainPage 마커 클릭 처리 완료 ===")

    def select_table_row_by_id(self, object_id: int):
        """객체 ID로 테이블 행 선택"""
        for row in range(self.table_object_list.rowCount()):
            item = self.table_object_list.item(row, 0)
            if item and int(item.text()) == object_id:
                self.table_object_list.selectRow(row)
                break

    def update_bird_risk(self, risk_level: Optional[BirdRiskLevel] = None):
        """조류 위험도 업데이트"""
        if risk_level is None:
            risk_level = BirdRiskLevel.LOW
        
        self.label_bird_risk_status.setText(risk_level.value)
        if risk_level == BirdRiskLevel.LOW:
            style = "background-color: #00FF00; color: #000000; border: 1px solid #008000;"
        elif risk_level == BirdRiskLevel.MEDIUM:
            style = "background-color: #FFFF00; color: #000000; border: 1px solid #FFA500;"
        else: # HIGH
            style = "background-color: #FF0000; color: #FFFFFF; border: 1px solid #8B0000;"
        self.label_bird_risk_status.setStyleSheet(f"{style} font-weight: bold; border-radius: 5px; padding: 5px;")
        
        if risk_level != BirdRiskLevel.LOW:
            self.bird_risk_alerted.emit(BirdRisk(risk_level))

    def update_runway_a_risk(self, risk_level: Optional[RunwayRiskLevel] = None):
        """활주로 A 위험도 업데이트"""
        if risk_level is None:
            risk_level = RunwayRiskLevel.LOW

        self.label_rwy_a_status.setText(risk_level.value)
        style = "background-color: #00FF00; color: #000000; border: 1px solid #008000;"
        if risk_level != RunwayRiskLevel.LOW:
            style = "background-color: #FF0000; color: #FFFFFF; border: 1px solid #8B0000;"
        self.label_rwy_a_status.setStyleSheet(f"{style} font-weight: bold; border-radius: 5px; padding: 5px;")
        
        if risk_level != RunwayRiskLevel.LOW:
            self.runway_risk_alerted.emit(RunwayRisk('A', risk_level))

    def update_runway_b_risk(self, risk_level: Optional[RunwayRiskLevel] = None):
        """활주로 B 위험도 업데이트"""
        if risk_level is None:
            risk_level = RunwayRiskLevel.LOW

        self.label_rwy_b_status.setText(risk_level.value)
        style = "background-color: #00FF00; color: #000000; border: 1px solid #008000;"
        if risk_level != RunwayRiskLevel.LOW:
            style = "background-color: #FF0000; color: #FFFFFF; border: 1px solid #8B0000;"
        self.label_rwy_b_status.setStyleSheet(f"{style} font-weight: bold; border-radius: 5px; padding: 5px;")
            
        if risk_level != RunwayRiskLevel.LOW:
            self.runway_risk_alerted.emit(RunwayRisk('B', risk_level))

    def update_object_detail(self, obj: DetectedObject):
        """객체 상세 정보 업데이트"""
        self.object_detail_dialog.update_object_info(obj)
        self.object_area.setCurrentIndex(2)

    def handle_object_detail_error(self, error_msg: str):
        """객체 상세보기 오류 처리"""
        QMessageBox.critical(self, "오류", f"객체 상세보기 오류: {error_msg}")

    def show_map(self):
        """지도 보기"""
        self.map_cctv_stack.setCurrentIndex(0)
        if self.network_manager and self.network_manager.udp_client.is_connected():
            self.network_manager.udp_client.disconnect()
        if self.network_manager:
            self.network_manager.request_map()

    def show_cctv(self):
        """CCTV 보기 (CCTV A 직접 연결)"""
        if self.network_manager:
            self.network_manager.request_cctv_a()

    def show_table(self):
        """테이블 보기"""
        self.object_area.setCurrentIndex(0)

    def show_detail(self):
        """상세보기"""
        row = self.table_object_list.currentRow()
        if row < 0:
            logger.warning("선택된 객체가 없음")
            return
        object_id = int(self.table_object_list.item(row, 0).text())
        self.network_manager.request_object_detail(object_id)

    def update_cctv_a_frame(self, frame: QImage, image_id: int = 0):
        """CCTV A 프레임 업데이트"""
        self.update_cctv_frame(self.label_cctv_1, frame, image_id, 'A')

    def update_cctv_b_frame(self, frame: QImage, image_id: int = 0):
        """CCTV B 프레임 업데이트"""
        self.update_cctv_frame(self.label_cctv_2, frame, image_id, 'B')

    def update_cctv_frame(self, label: QLabel, frame: QImage, image_id: int, cctv_id: str):
        """CCTV 프레임 공통 업데이트 로직"""
        try:
            if frame.isNull():
                logger.error(f"CCTV {cctv_id} 프레임이 Null: 이미지 ID {image_id}")
                return

            if cctv_id == 'A':
                current_time = time.time()
                self.cctv_a_frame_count += 1
                if self.cctv_a_last_time == 0: self.cctv_a_last_time = current_time
                elif current_time - self.cctv_a_last_time >= 1.0:
                    self.cctv_a_fps = self.cctv_a_frame_count / (current_time - self.cctv_a_last_time)
                    self.cctv_a_frame_count = 0
                    self.cctv_a_last_time = current_time
                fps = self.cctv_a_fps
            else: # cctv_id == 'B'
                current_time = time.time()
                self.cctv_b_frame_count += 1
                if self.cctv_b_last_time == 0: self.cctv_b_last_time = current_time
                elif current_time - self.cctv_b_last_time >= 1.0:
                    self.cctv_b_fps = self.cctv_b_frame_count / (current_time - self.cctv_b_last_time)
                    self.cctv_b_frame_count = 0
                    self.cctv_b_last_time = current_time
                fps = self.cctv_b_fps

            label_size = label.size()
            if label_size.width() <= 0 or label_size.height() <= 0: return

            scaled_pixmap = QPixmap.fromImage(frame).scaled(
                label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            
            if fps > 0:
                painter = QPainter(scaled_pixmap)
                painter.setPen(QPen(QColor(255, 255, 0)))
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                painter.drawText(10, 30, f"FPS: {fps:.1f}")
                painter.end()
            
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        except Exception as e:
            logger.error(f"CCTV {cctv_id} 프레임 업데이트 오류: {e}")

    def closeEvent(self, event):
        """위젯 종료 시 처리"""
        if hasattr(self, 'map_marker'):
            self.map_marker.clear_markers()
        
        # 시간 업데이트 타이머 정리
        if hasattr(self, 'time_update_timer'):
            self.time_update_timer.stop()
            
        super().closeEvent(event)

    def clear_object_list(self):
        """객체 목록 테이블을 완전히 초기화"""
        try:
            self.table_object_list.setRowCount(0)
            self.current_object_ids.clear()
            self.first_detected_object_ids.clear()
            self.object_last_seen.clear()
            
            if hasattr(self, 'map_marker'):
                self.map_marker.clear_all_markers()
            
            self.object_list_updated.emit(self.current_object_ids)
            logger.debug("객체 목록 테이블 초기화 완료")
            
        except Exception as e:
            logger.error(f"객체 목록 테이블 초기화 오류: {e}")

    def remove_object_from_table(self, object_id: int):
        """테이블에서 특정 객체 제거"""
        try:
            for row in range(self.table_object_list.rowCount()):
                item = self.table_object_list.item(row, 0)
                if item and int(item.text()) == object_id:
                    self.table_object_list.removeRow(row)
                    logger.debug(f"테이블에서 객체 ID {object_id} 제거")
                    break
        except Exception as e:
            logger.error(f"테이블에서 객체 제거 오류: {e}")

    def check_object_timeouts(self):
        """객체 타임아웃 확인 및 제거"""
        current_time = time.time()
        timeout_objects = []
        
        for object_id, last_seen in self.object_last_seen.items():
            if current_time - last_seen > self.object_timeout_seconds:
                timeout_objects.append(object_id)
        
        if timeout_objects:
            for object_id in timeout_objects:
                if object_id in self.current_object_ids:
                    self.current_object_ids.remove(object_id)
                    self.map_marker.remove_marker(object_id)
                    self.remove_object_from_table(object_id)
                    self.object_last_seen.pop(object_id, None)
                    
            logger.debug(f"타임아웃된 객체 제거: {timeout_objects}")

    def request_current_settings(self):
        """Main 탭 활성화 시 호출되는 메서드 - 현재 상태 새로고침"""
        try:
            logger.info("Main 페이지 활성화 - 현재 상태 새로고침")
            
            # 현재 객체 목록 새로고침 (필요시)
            if hasattr(self, 'current_object_ids') and self.current_object_ids:
                logger.debug(f"현재 감지된 객체 수: {len(self.current_object_ids)}")
            
            # 지도 뷰로 초기화 (기본 상태)
            self.show_map()
            
            # 조류/활주로 위험도 표시 새로고침
            self.refresh_risk_displays()
            
            # 현재 시간 업데이트
            self.update_current_time()
            
            logger.info("Main 페이지 새로고침 완료")
            
        except Exception as e:
            logger.error(f"Main 페이지 설정 요청 오류: {e}")

    def refresh_risk_displays(self):
        """위험도 표시 새로고침"""
        try:
            # 현재 설정된 위험도 다시 표시
            # 조류 위험도는 현재 값이 없으면 기본값으로 표시
            if not hasattr(self, '_current_bird_risk'):
                self.update_bird_risk(None)
            
            if not hasattr(self, '_current_runway_a_risk'):
                self.update_runway_a_risk(None)
                
            if not hasattr(self, '_current_runway_b_risk'):
                self.update_runway_b_risk(None)
                
            logger.debug("위험도 표시 새로고침 완료")
            
        except Exception as e:
            logger.error(f"위험도 표시 새로고침 오류: {e}")

    def clear_all_data(self):
        """모든 데이터 초기화"""
        try:
            # 객체 목록 초기화
            self.clear_object_list()
            
            # 마커 초기화
            if hasattr(self, 'map_marker'):
                self.map_marker.clear_all_markers()
            
            # 객체 ID 추적 초기화
            self.current_object_ids.clear()
            self.first_detected_object_ids.clear()
            self.object_last_seen.clear()
            
            # CCTV 프레임 초기화
            self.reset_cctv_displays()
            
            logger.info("Main 페이지 모든 데이터 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터 초기화 오류: {e}")

    def reset_cctv_displays(self):
        """CCTV 디스플레이 초기화"""
        try:
            # CCTV 라벨 초기화
            if hasattr(self, 'label_cctv_1'):
                self.label_cctv_1.clear()
                self.label_cctv_1.setText("CCTV A\n연결되지 않음")
                self.label_cctv_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.label_cctv_1.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; color: #666;")
            
            if hasattr(self, 'label_cctv_2'):
                self.label_cctv_2.clear()
                self.label_cctv_2.setText("CCTV B\n연결되지 않음")
                self.label_cctv_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.label_cctv_2.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; color: #666;")
            
            # FPS 카운터 초기화
            self.cctv_a_fps = 0
            self.cctv_b_fps = 0
            self.cctv_a_frame_count = 0
            self.cctv_b_frame_count = 0
            self.cctv_a_last_time = 0
            self.cctv_b_last_time = 0
            
            logger.debug("CCTV 디스플레이 초기화 완료")
            
        except Exception as e:
            logger.error(f"CCTV 디스플레이 초기화 오류: {e}")

    def get_current_status(self):
        """현재 페이지 상태 반환"""
        try:
            return {
                'object_count': len(self.current_object_ids),
                'current_view': 'map' if self.map_cctv_stack.currentIndex() == 0 else 'cctv',
                'bird_risk': getattr(self, '_current_bird_risk', None),
                'runway_a_risk': getattr(self, '_current_runway_a_risk', None),
                'runway_b_risk': getattr(self, '_current_runway_b_risk', None),
                'cctv_a_fps': self.cctv_a_fps,
                'cctv_b_fps': self.cctv_b_fps
            }
        except Exception as e:
            logger.error(f"현재 상태 확인 오류: {e}")
            return {}