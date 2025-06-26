import sys
import os
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi
from utils.interface import AccessControlSettings
from utils.network_manager import NetworkManager
from utils.logger import logger

class AccessPage(QWidget):
    def __init__(self, parent=None, network_manager=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/access_page.ui')
        loadUi(ui_path, self)
        
        # 네트워크 매니저 설정
        self.network_manager = network_manager
        
        # 현재 선택된 구역과 레벨
        self.current_zone = ""
        self.selected_level = 0
        
        # 구역별 현재 등급 (기본값)
        self.zone_levels = {
            'RWY A': 3, 'TWY A': 2, 'GRASS A': 1, 'TWY B': 2,
            'RWY B': 3, 'TWY C': 2, 'GRASS B': 1, 'TWY D': 2
        }
        
        # 색상 매핑
        self.level_colors = {
            1: "rgb(165, 214, 167)",  # 녹색 - 출입등급 1 (출입 허가)
            2: "rgb(255, 236, 179)",  # 노란색 - 출입등급 2 (작업자 출입 허가)  
            3: "rgb(255, 205, 210)"   # 빨간색 - 출입등급 3 (출입 불가)
        }
        
        self.setup_connections()
        self.setup_ui_styles()  # UI 스타일 설정
        self.update_zone_colors()        
        self.update_level_buttons()  # 초기 버튼 스타일 설정
        
        # 네트워크 시그널 연결
        if self.network_manager:
            self._connect_network_signals()            
        
    def setup_connections(self):
        """UI 이벤트 연결"""
        # 구역 클릭 이벤트 연결
        zones = ['RWY A', 'TWY A', 'GRASS A', 'TWY B', 'RWY B', 'TWY C', 'GRASS B', 'TWY D']
        zone_labels = [self.label_RWY_A, self.label_TWY_A, self.label_GRASS_A, self.label_TWY_B,
                      self.label_RWY_B, self.label_TWY_C, self.label_GRASS_B, self.label_TWY_D]
        
        for zone, label in zip(zones, zone_labels):
            label.mousePressEvent = lambda event, z=zone: self.zone_clicked(z)
            
        # 레벨 선택 버튼
        self.pushButton_level0.clicked.connect(lambda: self.level_selected(1))
        self.pushButton_level1.clicked.connect(lambda: self.level_selected(2))
        self.pushButton_level2.clicked.connect(lambda: self.level_selected(3))
        
        # 설정/취소 버튼
        self.pushButton_apply.clicked.connect(self.apply_setting)
        self.pushButton_cancel.clicked.connect(self.cancel_setting)
        
    def setup_ui_styles(self):
        """UI 요소들의 스타일 설정"""
        # horizontalLayoutWidget 초기에 숨김 (설정 페이지에서만 표시)
        self.horizontalLayoutWidget.setVisible(False)
        
        # apply, cancel 버튼 스타일 (normal_style 적용)
        button_style = """
            QPushButton {
                background-color: white; 
                color: #333; 
                border: 2px solid #999; 
                border-radius: 10px;
                font-weight: bold;
                font-size: 15px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        
        self.pushButton_apply.setStyleSheet(button_style)
        self.pushButton_cancel.setStyleSheet(button_style)
        
        # 설정 제목 스타일 (진한 글씨체)
        title_style = """
            QLabel {
                color: #333;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
                text-align: center;
            }
        """
        
        self.label_setting_title.setStyleSheet(title_style)
        
        # 레벨별 제목 스타일 (진한 글씨체)
        level_title_style = """
            QLabel {
                color: #333;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }
        """
        
        self.label_level0_title.setStyleSheet(level_title_style)
        self.label_level1_title.setStyleSheet(level_title_style)
        self.label_level2_title.setStyleSheet(level_title_style)
        
        # 설정 패널 스타일 (동적 적용)
        panel_style = """
            QWidget#widget_setting_panel {
                background-color: rgb(232, 232, 232);
                border: 2px solid rgb(153, 153, 153);
                border-radius: 20px;
            }
        """
        
        self.widget_setting_panel.setStyleSheet(panel_style)
        
    def _connect_network_signals(self):
        """네트워크 시그널 연결"""
        self.network_manager.access_control_settings_received.connect(self._on_settings_received)
        self.network_manager.access_control_update_result.connect(self._on_update_result)
        self.network_manager.access_control_error.connect(self._on_error)
        
    def zone_clicked(self, zone_name):
        """구역 클릭 처리"""
        self.current_zone = zone_name
        self.selected_level = self.zone_levels[zone_name]
        
        # 설정 패널로 전환
        self.stackedWidget_rightPanel.setCurrentIndex(1)
        self.label_setting_title.setText(f"{zone_name} 출입설정")
        
        # horizontalLayoutWidget 표시 (등급별 색상 안내)
        self.horizontalLayoutWidget.setVisible(True)
        
        # 현재 레벨 버튼 선택
        self.update_level_buttons()
        
    def level_selected(self, level):
        """레벨 선택 처리"""
        self.selected_level = level
        self.update_level_buttons()
        
    def update_level_buttons(self):
        """레벨 버튼 스타일 업데이트"""
        buttons = [self.pushButton_level0, self.pushButton_level1, self.pushButton_level2]
        button_levels = [1, 2, 3]  # 버튼에 대응하는 레벨
        
        # 선택된 버튼과 일반 버튼의 스타일 정의 (QPushButton 선택자 추가)
        selected_style = """
            QPushButton {
                background-color: #888; 
                color: white; 
                border: 2px solid #999; 
                border-radius: 10px;
                font-weight: bold;
            }
        """
        
        normal_style = """
            QPushButton {
                background-color: white; 
                color: #333; 
                border: 2px solid #999; 
                border-radius: 10px;
                font-weight: bold;
            }
        """
                
        for i, button in enumerate(buttons):
            if button_levels[i] == self.selected_level:
                button.setStyleSheet(selected_style)
            else:
                button.setStyleSheet(normal_style)    
                
    def apply_setting(self):
        """설정 적용"""
        try:
            # 로컬 설정 업데이트
            self.zone_levels[self.current_zone] = self.selected_level
            self.update_zone_colors()
            
            # 서버에 설정 업데이트 전송
            if self.network_manager:
                settings = self._create_access_control_settings()
                self.network_manager.update_access_control_settings(settings)
                logger.info(f"출입 제어 설정 업데이트 요청: {self.current_zone} = 레벨 {self.selected_level}")
            
            # 상태 패널로 돌아가기
            self.cancel_setting()
            
        except Exception as e:
            logger.error(f"설정 적용 실패: {e}")
        
    def cancel_setting(self):
        """설정 취소 - 상태 패널로 전환"""
        self.stackedWidget_rightPanel.setCurrentIndex(0)
        self.current_zone = ""
        
        # horizontalLayoutWidget 숨김 (상태 페이지에서는 불필요)
        self.horizontalLayoutWidget.setVisible(False)
        
    def update_zone_colors(self):
        """구역별 색상 업데이트"""
        zone_widgets = {
            'RWY A': self.label_RWY_A,
            'TWY A': self.label_TWY_A,
            'GRASS A': self.label_GRASS_A,
            'TWY B': self.label_TWY_B,
            'RWY B': self.label_RWY_B,
            'TWY C': self.label_TWY_C,
            'GRASS B': self.label_GRASS_B,
            'TWY D': self.label_TWY_D
        }
        
        for zone, widget in zone_widgets.items():
            level = self.zone_levels[zone]
            color = self.level_colors[level]
            widget.setStyleSheet(f"background-color: {color};")

    def request_current_settings(self):
        """서버에서 현재 출입 제어 설정 요청"""
        if self.network_manager:
            self.network_manager.request_access_control_settings()
            logger.info("출입 제어 설정 요청")

    def _create_access_control_settings(self) -> AccessControlSettings:
        """현재 설정을 AccessControlSettings 객체로 변환"""
        return AccessControlSettings(
            TWY_A_level=self.zone_levels['TWY A'],
            TWY_B_level=self.zone_levels['TWY B'],
            TWY_C_level=self.zone_levels['TWY C'],
            TWY_D_level=self.zone_levels['TWY D'],
            RWY_A_level=self.zone_levels['RWY A'],
            RWY_B_level=self.zone_levels['RWY B'],
            GRASS_A_level=self.zone_levels['GRASS A'],
            GRASS_B_level=self.zone_levels['GRASS B']
        )

    def _update_zone_levels_from_settings(self, settings: AccessControlSettings):
        """AccessControlSettings에서 구역 레벨 업데이트"""
        self.zone_levels.update({
            'TWY A': settings.TWY_A_level,
            'TWY B': settings.TWY_B_level,
            'TWY C': settings.TWY_C_level,
            'TWY D': settings.TWY_D_level,
            'RWY A': settings.RWY_A_level,
            'RWY B': settings.RWY_B_level,
            'GRASS A': settings.GRASS_A_level,
            'GRASS B': settings.GRASS_B_level
        })

    def _on_settings_received(self, settings: AccessControlSettings):
        """서버에서 출입 제어 설정 수신"""
        try:
            logger.info(f"출입 제어 설정 수신: {settings.to_dict()}")
            self._update_zone_levels_from_settings(settings)
            self.update_zone_colors()
            
        except Exception as e:
            logger.error(f"출입 제어 설정 처리 실패: {e}")

    def _on_update_result(self, success: bool, message: str):
        """출입 제어 설정 업데이트 결과 처리"""
        if success:
            logger.info(f"출입 제어 설정 업데이트 성공: {message}")
            # 성공 메시지박스 표시
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("설정 완료")
            msg_box.setText("설정이 적용되었습니다.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        else:
            logger.error(f"출입 제어 설정 업데이트 실패: {message}")
            # 실패 메시지박스 표시
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("설정 실패")
            msg_box.setText(f"설정 적용에 실패했습니다.\n{message}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

    def _on_error(self, error_message: str):
        """출입 제어 오류 처리"""
        logger.error(f"출입 제어 오류: {error_message}")

