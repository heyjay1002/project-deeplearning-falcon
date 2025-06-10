import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import logging
from pages.main_page import MainPage
from pages.access_page import AccessPage
from pages.log_page import LogPage

class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("FALCON")
        
        # MainPage 인스턴스 생성 및 셋팅
        main_page = MainPage(self)
        main_tab = self.tabWidget.widget(0)
        # 레이아웃이 없으면 생성
        if main_tab.layout() is None:
            from PyQt6.QtWidgets import QVBoxLayout
            main_tab.setLayout(QVBoxLayout())
        # 기존 위젯 제거
        for i in reversed(range(main_tab.layout().count())):
            widget_to_remove = main_tab.layout().itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
        # main_page 추가
        main_tab.layout().addWidget(main_page)

        # AccessPage 인스턴스 생성 및 셋팅
        access_page = AccessPage(self)
        access_tab = self.tabWidget.widget(1)
        if access_tab.layout() is None:
            from PyQt6.QtWidgets import QVBoxLayout
            access_tab.setLayout(QVBoxLayout())
        for i in reversed(range(access_tab.layout().count())):
            widget_to_remove = access_tab.layout().itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
        access_tab.layout().addWidget(access_page)

        # LogPage 인스턴스 생성 및 셋팅
        log_page = LogPage(self)
        log_tab = self.tabWidget.widget(2)
        if log_tab.layout() is None:
            from PyQt6.QtWidgets import QVBoxLayout
            log_tab.setLayout(QVBoxLayout())
        for i in reversed(range(log_tab.layout().count())):
            widget_to_remove = log_tab.layout().itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
        log_tab.layout().addWidget(log_page)

        # 탭 이름 설정
        self.tabWidget.setTabText(0, "Main")
        self.tabWidget.setTabText(1, "Access")
        self.tabWidget.setTabText(2, "Log")
        
        # 각 탭의 너비 설정
        tab_bar = self.tabWidget.tabBar()
        tab_bar.setStyleSheet("""
            QTabBar::tab {
                min-width: 150px;
            }
        """)        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowClass()
    window.show()
    sys.exit(app.exec())