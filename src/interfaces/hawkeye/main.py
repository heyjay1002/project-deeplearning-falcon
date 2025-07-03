import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import logging
from views.main_page import MainPage
from views.access_page import AccessPage
from views.log_page import LogPage
from views.notification_dialog import NotificationDialog
from utils.interface import DetectedObject, BirdRisk, RunwayRisk
from utils.network_manager import NetworkManager
from utils.logger import logger
from config.constants import BirdRiskLevel, RunwayRiskLevel

class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        # UI 파일 경로를 절대 경로로 설정
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui/main_window.ui")
        uic.loadUi(ui_file_path, self)
        self.setWindowTitle("FALCON")
        logger.info("FALCON 시작")
        
        # 창 크기 설정 
        self.resize(1320, 860)
        
        # 네트워크 매니저 생성
        self.network_manager = NetworkManager()
        
        # 상태바 설정
        self.setup_status_bar()
        
        # 탭 설정
        self.setup_tabs()
        
        # 네트워크 시그널 연결
        self._connect_network_signals()
        
        # 네트워크 서비스 시작
        self.network_manager.start_services()
        
        # 알림 중복 방지를 위한 변수들
        self._test_dialogs = []        

    def _connect_network_signals(self):
        nm = self.network_manager
        # 최초 감지 알림은 MainPage에서 처리하지만, 백업으로 메인 윈도우에서도 처리
        nm.first_object_detected.connect(self._handle_first_object_detected)
        nm.bird_risk_changed.connect(lambda risk: self.show_notification_dialog('bird', risk) if risk == BirdRiskLevel.HIGH else None)  # 조류 위험도 "경고"일 때만
        nm.runway_a_risk_changed.connect(lambda risk: self.show_notification_dialog('runway_a_risk', risk) if risk == RunwayRiskLevel.HIGH else None)  # 활주로 A 위험도 "경고"일 때만
        nm.runway_b_risk_changed.connect(lambda risk: self.show_notification_dialog('runway_b_risk', risk) if risk == RunwayRiskLevel.HIGH else None)  # 활주로 B 위험도 "경고"일 때만
        nm.tcp_connection_status_changed.connect(lambda connected, msg: self.update_connection_status(connected, msg, "TCP"))
        nm.udp_connection_status_changed.connect(lambda connected, msg: self.update_connection_status(connected, msg, "UDP"))

    def _handle_first_object_detected(self, obj):
        """최초 감지 이벤트 백업 처리 - MainPage에서 처리되지 않는 경우를 대비"""
        try:
            # MainPage가 이미 처리했는지 확인
            if hasattr(self, 'main_page') and self.main_page:
                # MainPage에서 이미 처리된 경우 중복 방지
                if obj.object_id in self.main_page.first_detected_object_ids:
                    logger.debug(f"MainPage에서 이미 처리된 객체: ID {obj.object_id}")
                    return
            
            # MainPage에서 처리되지 않은 경우 백업으로 처리
            self.show_notification_dialog('object', obj)
            logger.info(f"메인 윈도우에서 최초 감지 백업 처리: ID {obj.object_id} ({obj.object_type.value})")
            
        except Exception as e:
            logger.error(f"최초 감지 백업 처리 실패: {e}")

    def setup_status_bar(self):
        """상태바 설정"""
        # 연결 상태 추적 변수
        self.tcp_connected = False
        self.udp_connected = False
        
        # TCP 연결 상태 표시기창
        self.tcp_indicator = QLabel("●")
        self.tcp_indicator.setToolTip("TCP 연결 상태")
        self.tcp_indicator.setStyleSheet("color: #ccc; font-size: 16px;")
        
        # UDP 연결 상태 표시기  
        self.udp_indicator = QLabel("●")
        self.udp_indicator.setToolTip("UDP 연결 상태")
        self.udp_indicator.setStyleSheet("color: #ccc; font-size: 16px;")
        
        # 상태바에 위젯 추가
        self.statusbar.addWidget(QLabel("TCP:"))
        self.statusbar.addWidget(self.tcp_indicator)
        self.statusbar.addWidget(QLabel("UDP:"))
        self.statusbar.addWidget(self.udp_indicator)

    def update_connection_status(self, is_connected: bool, message: str, connection_type: str = "TCP"):
        """연결 상태 업데이트"""
        # 연결 상태 추적 업데이트
        if connection_type == "TCP":
            self.tcp_connected = is_connected
            # TCP 표시기 업데이트
            if is_connected:
                self.tcp_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
                self.tcp_indicator.setToolTip("TCP 연결됨")
            else:
                # 재연결 시도 중인지 확인
                if (self.network_manager and 
                    self.network_manager.tcp_client and 
                    self.network_manager.tcp_client.reconnect_timer.isActive()):
                    # 재연결 시도 중 - 노란색
                    self.tcp_indicator.setStyleSheet("color: #FFC107; font-size: 16px;")
                    self.tcp_indicator.setToolTip("TCP 재연결 시도 중")
                else:
                    # 연결 끊김 - 빨간색
                    self.tcp_indicator.setStyleSheet("color: #F44336; font-size: 16px;")
                    self.tcp_indicator.setToolTip("TCP 연결 끊김")
                
        elif connection_type == "UDP":
            self.udp_connected = is_connected
            # UDP 표시기 업데이트
            if is_connected:
                self.udp_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
                self.udp_indicator.setToolTip("UDP 연결됨")
            else:
                self.udp_indicator.setStyleSheet("color: #F44336; font-size: 16px;")
                self.udp_indicator.setToolTip("UDP 연결 끊김")

    def setup_tabs(self):
        """탭 설정 및 페이지 추가"""
        # MainPage 인스턴스 생성 시 network_manager를 전달
        self.main_page = MainPage(self, network_manager=self.network_manager)
        self._setup_tab_widget(0, self.main_page)

        # AccessPage 인스턴스 생성 및 셋팅
        self.access_page = AccessPage(self, network_manager=self.network_manager)
        self._setup_tab_widget(1, self.access_page)

        # LogPage 인스턴스 생성 및 셋팅
        self.log_page = LogPage(self, network_manager=self.network_manager)
        self._setup_tab_widget(2, self.log_page)

        # 탭 이름 설정
        self.tabWidget.setTabText(0, "Main")
        self.tabWidget.setTabText(1, "Access")
        self.tabWidget.setTabText(2, "Log")
        
        # 탭 전환 이벤트 연결
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
        
        # 탭 스타일 설정
        self._setup_tab_style()

    def _setup_tab_widget(self, tab_index: int, widget: QWidget):
        """개별 탭 위젯 설정"""
        tab = self.tabWidget.widget(tab_index)
        
        # 레이아웃이 없으면 생성
        if tab.layout() is None:
            tab.setLayout(QVBoxLayout())
        
        # 기존 위젯 제거
        layout = tab.layout()
        for i in reversed(range(layout.count())):
            widget_to_remove = layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
        
        # 새 위젯 추가
        layout.addWidget(widget)

    def _setup_tab_style(self):
        """탭 스타일 설정"""
        tab_bar = self.tabWidget.tabBar()
        tab_bar.setStyleSheet("""
            QTabBar::tab {
                min-width: 150px;
            }
        """)

    def _on_tab_changed(self, index):
        """탭 전환 이벤트 처리"""
        if index == 1:  # Access 탭이 선택된 경우
            logger.info("Access 탭 전환")
            if hasattr(self, 'access_page') and self.access_page:
                self.access_page.request_current_settings()

        elif index == 2:  # Log 탭이 선택된 경우
            logger.info("Log 탭 전환")
            if hasattr(self, 'log_page') and self.log_page:
                self.log_page.request_current_settings()

    def show_notification_dialog(self, dialog_type, data):
        """알림 다이얼로그 표시 - 중복 방지 로직 추가"""
        # 위험도 알림의 경우 팝업 없이 로그만 기록
        if dialog_type in ['bird', 'runway_a_risk', 'runway_b_risk']:
            self._log_notification_details(dialog_type, data)
            return
        
        # 기존에 삭제된 다이얼로그들 먼저 정리
        valid_dialogs = []
        for dialog in self._test_dialogs:
            try:
                # 삭제된 객체인지 확인
                if dialog.isVisible():
                    valid_dialogs.append(dialog)
            except RuntimeError:
                # 이미 삭제된 객체는 무시
                pass
        self._test_dialogs = valid_dialogs
        
        # 기존 알림창 중복 확인
        for existing_dialog in self._test_dialogs:
            try:
                if existing_dialog.isVisible() and existing_dialog.notification_type == dialog_type:
                    # 객체 알림의 경우 ID로 중복 확인 (object, violation_access, rescue 모두)
                    if dialog_type in ['object', 'violation_access', 'rescue'] and hasattr(data, 'object_id') and hasattr(existing_dialog.data, 'object_id'):
                        if data.object_id == existing_dialog.data.object_id:
                            logger.debug(f"중복 알림 방지: 타입 {dialog_type}, ID {data.object_id}")
                            return
            except RuntimeError:
                # 이미 삭제된 객체는 무시
                continue
        
        # 새 알림창 생성
        dialog = NotificationDialog(dialog_type, data, self)
        self._test_dialogs.append(dialog)
        dialog.show()
        
        # 알림 표시 로그 기록
        self._log_notification_details(dialog_type, data)

    def debug_show_notification_dialog(self, dialog_type, data):
        print(f"[DEBUG] 알림 다이얼로그 호출됨: {dialog_type}, {data}")
        if not hasattr(self, '_test_dialogs'):
            self._test_dialogs = []
        dialog = NotificationDialog(dialog_type, data, self)
        self._test_dialogs.append(dialog)
        dialog.show()

    def _log_notification_details(self, dialog_type, data):
        """알림 표시 시 상세 정보를 로그로 기록"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if dialog_type == 'object' and hasattr(data, 'object_id'):
                # 객체 감지 알림
                object_type = data.object_type.value if hasattr(data.object_type, 'value') else str(data.object_type)
                area = data.area.value if hasattr(data.area, 'value') else str(data.area)
                risk_level = getattr(data, 'state_info', 0)
                
                logger.info(f"[알림 표시] 객체 감지 - ID: {data.object_id}, 타입: {object_type}, 위치: {area}, 위험도: {risk_level}, 좌표: ({data.x_coord}, {data.y_coord}), 시간: {current_time}")
                
            elif dialog_type == 'rescue' and hasattr(data, 'object_id'):
                # 구조 요청 알림
                object_type = data.object_type.value if hasattr(data.object_type, 'value') else str(data.object_type)
                area = data.area.value if hasattr(data.area, 'value') else str(data.area)
                risk_level = getattr(data, 'state_info', 0)
                
                logger.warning(f"[알림 표시] 구조 요청 - ID: {data.object_id}, 타입: {object_type}, 위치: {area}, 위험도: {risk_level}, 좌표: ({data.x_coord}, {data.y_coord}), 시간: {current_time}")
                
            elif dialog_type == 'violation_access' and hasattr(data, 'object_id'):
                # 출입 위반 알림
                object_type = data.object_type.value if hasattr(data.object_type, 'value') else str(data.object_type)
                area = data.area.value if hasattr(data.area, 'value') else str(data.area)
                risk_level = getattr(data, 'state_info', 0)
                
                logger.info(f"[알림 표시] 출입 위반 - ID: {data.object_id}, 타입: {object_type}, 위치: {area}, 위험도: {risk_level}, 좌표: ({data.x_coord}, {data.y_coord}), 시간: {current_time}")
                
            elif dialog_type in ['bird', 'runway_a_risk', 'runway_b_risk']:
                # 위험도 알림
                risk_type = {
                    'bird': '조류 위험도',
                    'runway_a_risk': '활주로 A 위험도', 
                    'runway_b_risk': '활주로 B 위험도'
                }.get(dialog_type, '위험도')
                
                risk_value = data.value if hasattr(data, 'value') else str(data)
                logger.info(f"[알림 표시] {risk_type} - 레벨: {risk_value}, 시간: {current_time}")
                
            else:
                # 기타 알림
                logger.info(f"[알림 표시] 타입: {dialog_type}, 데이터: {data}, 시간: {current_time}")
                
        except Exception as e:
            logger.error(f"알림 로그 기록 실패: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowClass()
    window.show()       
    sys.exit(app.exec())