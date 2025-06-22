import sys
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

class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("FALCON")
        
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

    def _connect_network_signals(self):
        nm = self.network_manager
        nm.object_detected.connect(lambda obj: self.show_notification_dialog('object', obj))
        nm.bird_risk_changed.connect(lambda risk: self.show_notification_dialog('bird', risk))
        nm.runway_a_risk_changed.connect(lambda risk: self.show_notification_dialog('runway_a_risk', risk))
        nm.runway_b_risk_changed.connect(lambda risk: self.show_notification_dialog('runway_b_risk', risk))
        nm.tcp_connection_status_changed.connect(lambda connected, msg: self.update_connection_status(connected, msg, "TCP"))
        nm.udp_connection_status_changed.connect(lambda connected, msg: self.update_connection_status(connected, msg, "UDP"))

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
        access_page = AccessPage(self)
        self._setup_tab_widget(1, access_page)

        # LogPage 인스턴스 생성 및 셋팅
        log_page = LogPage(self)
        self._setup_tab_widget(2, log_page)

        # 탭 이름 설정
        self.tabWidget.setTabText(0, "Main")
        self.tabWidget.setTabText(1, "Access")
        self.tabWidget.setTabText(2, "Log")
        
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

    def show_notification_dialog(self, dialog_type, data):
        """알림 다이얼로그 표시"""
        if not hasattr(self, '_test_dialogs'):
            self._test_dialogs = []
        dialog = NotificationDialog(dialog_type, data, self)
        self._test_dialogs.append(dialog)
        dialog.show()

    def debug_show_notification_dialog(self, dialog_type, data):
        print(f"[DEBUG] 알림 다이얼로그 호출됨: {dialog_type}, {data}")
        if not hasattr(self, '_test_dialogs'):
            self._test_dialogs = []
        dialog = NotificationDialog(dialog_type, data, self)
        self._test_dialogs.append(dialog)
        dialog.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowClass()
    window.show()       
    sys.exit(app.exec())