#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.uic import loadUi

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from views.access_page import AccessPage
from utils.interface import AccessControlSettings
from utils.network_manager import NetworkManager
from utils.logger import logger

class MockNetworkManager(NetworkManager):
    """테스트용 가짜 네트워크 매니저"""
    
    # 시그널을 클래스 변수로 정의
    access_control_settings_received = pyqtSignal(AccessControlSettings)
    access_control_update_result = pyqtSignal(bool, str)
    access_control_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        # 부모 클래스 초기화는 건너뛰고 QObject만 초기화
        from PyQt6.QtCore import QObject
        QObject.__init__(self, parent)
        
    def request_access_control_settings(self):
        """가짜 AC_AC 요청 - 타이머로 지연된 응답 시뮬레이션"""
        logger.info("🔄 [MOCK] AC_AC 요청 송신됨")
        
        # 1초 후 가짜 응답 전송
        QTimer.singleShot(1000, self._send_fake_response)
        
    def _send_fake_response(self):
        """가짜 AR_AC 응답 시뮬레이션"""
        # 테스트 데이터: TWY_A=3, TWY_B=2, TWY_C=1, TWY_D=1, RWY_A=3, RWY_B=2, GRASS_A=3, GRASS_B=3
        fake_settings = AccessControlSettings(
            TWY_A_level=3,    # 1: TWY_A
            TWY_B_level=2,    # 2: TWY_B  
            TWY_C_level=1,    # 3: TWY_C
            TWY_D_level=1,    # 4: TWY_D
            RWY_A_level=3,    # 5: RWY_A
            RWY_B_level=2,    # 6: RWY_B
            GRASS_A_level=3,  # 7: GRASS_A
            GRASS_B_level=3,  # 8: GRASS_B
    
        )
        
        logger.info("📥 [MOCK] AR_AC 응답 수신: OK,3,2,1,1,3,2,3,3")
        logger.info(f"📊 [MOCK] 파싱된 설정: {fake_settings.to_dict()}")
        
        # 시그널 발생으로 AccessPage에 전달
        self.access_control_settings_received.emit(fake_settings)
        
    def update_access_control_settings(self, settings: AccessControlSettings):
        """가짜 AC_UA 요청"""
        logger.info(f"🔄 [MOCK] AC_UA 요청 송신됨: {settings.to_string()}")
        
        # 0.5초 후 성공 응답
        QTimer.singleShot(500, lambda: self._send_update_response(True))
        
    def _send_update_response(self, success: bool):
        """가짜 업데이트 응답"""
        if success:
            logger.info("✅ [MOCK] AR_UA 응답: 설정 업데이트 성공")
            self.access_control_update_result.emit(True, "설정이 성공적으로 업데이트되었습니다.")
        else:
            logger.error("❌ [MOCK] AR_UA 응답: 설정 업데이트 실패")
            self.access_control_update_result.emit(False, "설정 업데이트에 실패했습니다.")

class TestMainWindow(QMainWindow):
    """테스트용 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # UI 파일 로드
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui/main_window.ui")
        loadUi(ui_file_path, self)
        self.setWindowTitle("FALCON - Access Test")
        
        logger.info("🚀 테스트 시작: Access 탭 시뮬레이션")
        
        # 창 크기 설정 
        self.resize(1320, 860)
        
        # 가짜 네트워크 매니저 생성
        self.network_manager = MockNetworkManager()
        
        # 탭 설정
        self.setup_tabs()
        
        # 탭 전환 이벤트 연결
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
        
        # 초기 상태 로깅
        logger.info("📋 초기 구역별 등급:")
        for zone, level in self.access_page.zone_levels.items():
            logger.info(f"  {zone}: 등급 {level}")
            
    def setup_tabs(self):
        """탭 설정"""
        # AccessPage 인스턴스 생성 시 mock network_manager를 전달
        self.access_page = AccessPage(self, network_manager=self.network_manager)
        self._setup_tab_widget(1, self.access_page)
        
        # 탭 이름 설정
        self.tabWidget.setTabText(0, "Main")
        self.tabWidget.setTabText(1, "Access")
        self.tabWidget.setTabText(2, "Log")
        
    def _setup_tab_widget(self, tab_index: int, widget):
        """개별 탭 위젯 설정"""
        from PyQt6.QtWidgets import QVBoxLayout
        
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
        
    def _on_tab_changed(self, index):
        """탭 전환 이벤트 처리"""
        if index == 1:  # Access 탭이 선택된 경우
            logger.info("🔔 Access 탭 선택됨!")
            logger.info("📡 서버에 AC_AC 명령 송신 중...")
            
            if hasattr(self, 'access_page') and self.access_page:
                self.access_page.request_current_settings()

def main():
    """테스트 실행"""
    app = QApplication(sys.argv)
    
    # 로그 설정
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    window = TestMainWindow()
    window.show()
    
    # 안내 메시지
    logger.info("=" * 50)
    logger.info("🎯 테스트 방법:")
    logger.info("1. 'Access' 탭을 클릭하세요")
    logger.info("2. 1초 후 가짜 서버 응답이 옵니다")
    logger.info("3. 구역별 색상이 변경되는지 확인하세요")
    logger.info("4. 구역을 클릭해서 설정 변경도 테스트하세요")
    logger.info("=" * 50)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 