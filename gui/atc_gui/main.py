import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import logging
from views.main_page import MainPage
from views.access_page import AccessPage
from views.log_page import LogPage

class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("FALCON")
        
        # 창 상태를 명시적으로 일반 상태로 설정
        self.setWindowState(Qt.WindowState.WindowNoState)
        
        # 창 크기 설정 (더 명확하게)
        self.resize(1320, 860)
        
        # 최소/최대 크기 제한 (선택사항)
        self.setMinimumSize(800, 600)
        self.setMaximumSize(1920, 1080)
        
        # 창을 화면 중앙에 배치
        self.center_window()
        
        # 상태바 설정
        self.setup_status_bar()
        
        # 탭 설정
        self.setup_tabs()

    def center_window(self):
        """창을 화면 중앙에 배치"""
        # 현재 화면의 geometry 가져오기
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # 창의 geometry 계산
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        
        # 창 위치 설정
        self.move(x, y)

    def setup_status_bar(self):
        """상태바 설정"""
        # 연결 상태 추적 변수
        self.tcp_connected = False
        self.udp_connected = False
        
        # TCP 연결 상태 표시기
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
        # MainPage 인스턴스 생성 및 셋팅
        self.main_page = MainPage(self)
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
        
        # MainPage의 연결 상태 시그널을 상태바와 연결
        if hasattr(self.main_page, 'network_manager'):
            self.main_page.network_manager.tcp_connection_status_changed.connect(
                lambda connected, msg: self.update_connection_status(connected, msg, "TCP")
            )
            self.main_page.network_manager.udp_connection_status_changed.connect(
                lambda connected, msg: self.update_connection_status(connected, msg, "UDP")
            )

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
                padding: 8px 16px;
            }
        """)

    def showEvent(self, event):
        """창이 표시될 때 호출되는 이벤트"""
        super().showEvent(event)
        # 창이 표시된 후에도 크기와 상태를 다시 확인
        if self.windowState() != Qt.WindowState.WindowNoState:
            self.setWindowState(Qt.WindowState.WindowNoState)
            self.resize(1320, 860)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 애플리케이션 레벨에서 창 상태 제어
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    
    window = WindowClass()
    window.show()
    
    # 창이 표시된 후 한 번 더 크기 조정 (강제)
    QTimer.singleShot(100, lambda: window.resize(1320, 860))
    
    sys.exit(app.exec())