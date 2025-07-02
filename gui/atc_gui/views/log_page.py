from PyQt6.QtWidgets import QWidget, QComboBox, QLabel, QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QDate
from config.constants import MessagePrefix
from utils.interface import PilotLog, ObjectDetectionLog, BirdRiskLog
from utils.logger import logger
import os

class LogPage(QWidget):
    def __init__(self, parent=None, network_manager=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/log_page.ui')
        uic.loadUi(ui_path, self)
        
        # 네트워크 매니저 설정
        self.network_manager = network_manager
        
        # 필터링을 위한 원본 객체 감지 데이터 저장
        self.original_object_data = []
        
        # UI 초기 설정
        self.setup_ui()
        
        # 시그널 연결
        self.setup_connections()
        
        # 네트워크 시그널 연결
        if self.network_manager:
            self.setup_network_signals()

    def setup_ui(self):
        """UI 초기 설정"""
        # 초기 날짜 설정 (오늘 날짜 기준)
        today = QDate.currentDate()
        self.start_date.setDate(today.addDays(-30))  # 30일 전부터
        self.end_date.setDate(today)  # 오늘까지
        
        # 버튼 스타일 설정
        self.setup_button_styles()
        
        # 테이블 설정 - 약간의 지연을 두고 설정
        self.setup_all_tables()
        
        # combo_log 첫 번째 항목 선택 및 초기 페이지 설정
        self.combo_log.setCurrentIndex(0)  # 첫 번째 항목 선택
        self.stackedWidget.setCurrentIndex(0)  # page_object가 기본
        
        # 첫 번째 테이블(객체 감지) 미리 초기화
        self.initialize_current_table(0)

    def apply_table_style(self, table):
        """테이블 스타일 적용"""
        try:
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
            
            # 행 높이 설정
            table.verticalHeader().setDefaultSectionSize(40)
            
            # 테이블 여백 설정
            table.setShowGrid(True)
            
        except Exception as e:
            logger.error(f"테이블 스타일 적용 오류: {e}")

    def setup_button_styles(self):
        """버튼 스타일 설정"""
        try:
            # 조회 버튼 스타일 (돋보기 아이콘 포함)
            search_style = """
                QPushButton {
                    background-color: #17a2b8;
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 4px;
                    min-width: 80px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
                QPushButton:pressed {
                    background-color: #11707f;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """
            show_img_style = """
                QPushButton {
                    background-color: #484848;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    padding: 2px 2px;
                    font-size: 14px;
                    min-width: 80px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background-color: #5c5c5c;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
            """
           
            # 버튼에 스타일 적용
            if hasattr(self, 'btn_search'):
                self.btn_search.setStyleSheet(search_style)
                # 돋보기 아이콘 텍스트 추가
                self.btn_search.setText("🔍 조회")
                
            if hasattr(self, 'btn_show_img'):
                self.btn_show_img.setStyleSheet(show_img_style)
                
            # 필터 적용 버튼 스타일 (객체 감지용)
            filter_style = """
                QPushButton {
                    background-color: #28a745;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    padding: 2px 2px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """               
            
            if hasattr(self, 'btn_filter_on'):
                self.btn_filter_on.setStyleSheet(filter_style)

        
            # 필터 적용 버튼 스타일 (객체 감지용)
            reset_style = """
                QPushButton {
                    background-color: #6c757d;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    padding: 2px 2px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
                QPushButton:pressed {
                    background-color: #545b62;
                }
            """
            
            if hasattr(self, 'btn_reset'):
                self.btn_reset.setStyleSheet(reset_style)
            
        except Exception as e:
            logger.error(f"버튼 스타일 설정 오류: {e}")

    def setup_all_tables(self):
        """모든 테이블을 설정하고 강제로 표시"""
        
        # 테이블 존재 여부 확인 - 실제 UI 파일의 위젯 이름 사용
        tables = ['tableWidget_object', 'tableWidget_bird', 'tableWidget_pilot']
        for table_name in tables:
            if hasattr(self, table_name):
                table = getattr(self, table_name)
                # 테이블을 강제로 표시
                table.show()
                table.setVisible(True)
            else:
                logger.error(f"{table_name}이 존재하지 않습니다")
        
        self.setup_object_table()
        self.setup_bird_table()
        self.setup_pilot_table()

    def setup_object_table(self):
        """객체 감지 로그 테이블 초기 설정"""
        try:
            if not hasattr(self, 'tableWidget_object'):
                logger.error("tableWidget_object 위젯이 존재하지 않습니다")
                return
                
            table = self.tableWidget_object
            
            # 테이블을 강제로 표시
            table.show()
            table.setVisible(True)
            
            # 객체 감지 테이블 헤더 설정 ("No." 컬럼 추가, 이벤트 타입 제거)
            object_headers = ["No.", "객체 ID", "객체 종류", "구역", "시간"]
            table.setColumnCount(len(object_headers))
            table.setHorizontalHeaderLabels(object_headers)
            
            # 컬럼 기본 너비 설정 (Stretch 모드에서 초기 비율 설정)
            table.setColumnWidth(0, 60)   # No. (좁게)
            table.setColumnWidth(1, 100)  # 객체 ID
            table.setColumnWidth(2, 120)  # 객체 종류
            table.setColumnWidth(3, 100)  # 구역
            table.setColumnWidth(4, 200)  # 시간 (넓게)
            
            # 테이블 초기화
            table.setRowCount(0)
            
            # 테이블 속성 설정
            table.setAlternatingRowColors(True)  # 행 색상 교대로 표시
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # 행 전체 선택
            table.verticalHeader().setVisible(False)  # 행 번호 숨기기
            
            # 폰트 크기 설정
            font = table.font()
            font.setPointSize(12)
            table.setFont(font)
            
            # 테이블 스타일 적용
            self.apply_table_style(table)
            
            # 컬럼별 개별 크기 조정 모드 설정
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # No. - 고정 크기
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # 객체 ID - 동일 너비
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # 객체 종류 - 동일 너비
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # 구역 - 동일 너비
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # 시간 - 동일 너비

        except Exception as e:
            logger.error(f"객체 테이블 설정 오류: {e}")

    def setup_bird_table(self):
        """조류 위험도 로그 테이블 초기 설정"""
        try:
            if not hasattr(self, 'tableWidget_bird'):
                logger.error("tableWidget_bird 위젯이 존재하지 않습니다")
                return
                
            table = self.tableWidget_bird
            
            # 테이블을 강제로 표시
            table.show()
            table.setVisible(True)
            
            # 조류 위험도 테이블 헤더 설정 ("No." 컬럼 추가)
            bird_headers = ["No.", "조류 위험도", "시간"]
            table.setColumnCount(len(bird_headers))
            table.setHorizontalHeaderLabels(bird_headers)
            
            # 컬럼 기본 너비 설정 (Stretch 모드에서 초기 비율 설정)
            table.setColumnWidth(0, 60)   # No. (좁게)
            table.setColumnWidth(1, 150)  # 조류 위험도
            table.setColumnWidth(2, 200)  # 시간
            
            # 테이블 초기화
            table.setRowCount(0)
            
            # 테이블 속성 설정
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.verticalHeader().setVisible(False)  # 행 번호 숨기기
            
            # 폰트 크기 설정
            font = table.font()
            font.setPointSize(12)
            table.setFont(font)
            
            # 테이블 스타일 적용
            self.apply_table_style(table)
            
            # 컬럼별 개별 크기 조정 모드 설정
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # No. - 고정 크기
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # 조류 위험도 - 동일 너비
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # 시간 - 동일 너비
            
        except Exception as e:
            logger.error(f"조류 테이블 설정 오류: {e}")

    def setup_pilot_table(self):
        """파일럿 로그 테이블 초기 설정"""
        try:
            if not hasattr(self, 'tableWidget_pilot'):
                logger.error("tableWidget_pilot 위젯이 존재하지 않습니다")
                return
                
            table = self.tableWidget_pilot

            # 테이블을 강제로 표시
            table.show()
            table.setVisible(True)
            
            # 파일럿 테이블 헤더 설정 ("No." 컬럼 추가)
            pilot_headers = ["No.", "요청 타입", "응답 타입", "요청 시간", "응답 시간"]
            table.setColumnCount(len(pilot_headers))
            table.setHorizontalHeaderLabels(pilot_headers)
            
            # 컬럼 기본 너비 설정 (Stretch 모드에서 초기 비율 설정)
            table.setColumnWidth(0, 60)   # No. (좁게)
            table.setColumnWidth(1, 150)  # 요청 타입
            table.setColumnWidth(2, 150)  # 응답 타입
            table.setColumnWidth(3, 200)  # 요청 시간
            table.setColumnWidth(4, 200)  # 응답 시간
            
            # 테이블 초기화
            table.setRowCount(0)
            
            # 테이블 속성 설정
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.verticalHeader().setVisible(False)  # 행 번호 숨기기
            
            # 폰트 크기 설정
            font = table.font()
            font.setPointSize(12)
            table.setFont(font)
            
            # 테이블 스타일 적용
            self.apply_table_style(table)
            
            # 컬럼별 개별 크기 조정 모드 설정
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # No. - 고정 크기
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # 요청 타입 - 동일 너비
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # 응답 타입 - 동일 너비
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # 요청 시간 - 동일 너비
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # 응답 시간 - 동일 너비
          
        except Exception as e:
            logger.error(f"파일럿 테이블 설정 오류: {e}")

    def initialize_current_table(self, index):
        """현재 선택된 테이블을 초기화하고 강제 표시"""
        try:
            if index == 0:  # 객체 감지 이력
                if hasattr(self, 'tableWidget_object'):
                    self.tableWidget_object.setRowCount(0)
                    self.tableWidget_object.show()
                    self.tableWidget_object.setVisible(True)
            elif index == 1:  # 조류 위험도 등급 변화 이력
                if hasattr(self, 'tableWidget_bird'):
                    self.tableWidget_bird.setRowCount(0)
                    self.tableWidget_bird.show()
                    self.tableWidget_bird.setVisible(True)
            elif index == 2:  # 조종사 요청 응답 이력
                if hasattr(self, 'tableWidget_pilot'):
                    self.tableWidget_pilot.setRowCount(0)
                    self.tableWidget_pilot.show()
                    self.tableWidget_pilot.setVisible(True)
        except Exception as e:
            logger.error(f"테이블 초기화 오류 (인덱스 {index}): {e}")

    def setup_connections(self):
        """시그널 연결 설정"""
        # 검색 버튼 클릭 시그널 연결
        self.btn_search.clicked.connect(self.on_search_clicked)
        
        # 이미지 보기 버튼 클릭 시그널 연결
        self.btn_show_img.clicked.connect(self.on_show_image_clicked)
        
        # 필터 적용 버튼 클릭 시그널 연결
        if hasattr(self, 'btn_filter_on'):
            self.btn_filter_on.clicked.connect(self.on_filter_apply_clicked)
        
        # 리셋 버튼 클릭 시그널 연결
        if hasattr(self, 'btn_reset'):
            self.btn_reset.clicked.connect(self.on_reset_clicked)
        
        # 콤보박스 변경 시 페이지 전환 및 테이블 초기화
        self.combo_log.currentIndexChanged.connect(self.on_log_type_changed)

    def setup_network_signals(self):
        """네트워크 시그널 연결"""
        try:
            # TCP 클라이언트 시그널 연결
            tcp_client = self.network_manager.tcp_client
            if tcp_client:
                # 파일럿 로그 응답 시그널 연결
                tcp_client.pilot_log_response.connect(self.on_pilot_log_received)
                tcp_client.pilot_log_error.connect(self.on_pilot_log_error)
                # 객체 감지 로그 응답 시그널 연결
                tcp_client.object_detection_log_response.connect(self.on_object_detection_log_received)
                tcp_client.object_detection_log_error.connect(self.on_object_detection_log_error)
                # 조류 위험도 로그 응답 시그널 연결
                tcp_client.bird_risk_log_response.connect(self.on_bird_risk_log_received)
                tcp_client.bird_risk_log_error.connect(self.on_bird_risk_log_error)
                # 로그 페이지 전용 객체 이미지 시그널 연결
                tcp_client.log_object_image_response.connect(self.on_object_image_received)
                tcp_client.log_object_image_error.connect(self.on_object_image_error)
                logger.info("모든 로그 시그널 연결 완료")
        except Exception as e:
            logger.error(f"네트워크 시그널 연결 오류: {e}")

    def on_log_type_changed(self, index):
        """로그 타입 변경 시 페이지 전환 및 테이블 초기화"""
        try:
            # combo_log 항목 순서대로 페이지 전환
            # 0: 위험요소 감지 이력 -> page_object (index 0)
            # 1: 조류 위험도 등급 변화 이력 -> page_bird (index 1)  
            # 2: 조종사 요청 응답 이력 -> page_pilot (index 2)
            self.stackedWidget.setCurrentIndex(index)
            
            # 선택된 테이블 초기화
            self.initialize_current_table(index)
            
            logger.info(f"로그 타입 변경: {self.combo_log.currentText()}, 페이지 인덱스: {index}")
            
        except Exception as e:
            logger.error(f"로그 타입 변경 처리 오류: {e}")

    def on_search_clicked(self):
        """검색 버튼 클릭 처리"""
        try:
            # 현재 선택된 로그 타입 확인
            log_type_index = self.combo_log.currentIndex()
            log_type_text = self.combo_log.currentText()
            
            # 날짜 정보 가져오기
            start_date = self.start_date.date()
            end_date = self.end_date.date()
            
            # 날짜를 문자열로 변환 (YYYY-MM-DD 형식)
            start_time = start_date.toString("yyyy-MM-dd")
            end_time = end_date.toString("yyyy-MM-dd")
            
            logger.info(f"로그 검색 요청: {log_type_text}, 기간: {start_time} ~ {end_time}")
            
            # 페이지 전환
            self.stackedWidget.setCurrentIndex(log_type_index)
            
            # 네트워크 매니저가 없으면 경고 메시지 표시
            if not self.network_manager:
                QMessageBox.warning(self, "오류", "네트워크 연결이 설정되지 않았습니다.")
                return
            
            # 로그 타입에 따라 적절한 메시지 전송
            if log_type_index == 0:  # 위험요소 감지 이력
                self.request_object_log(start_time, end_time)
            elif log_type_index == 1:  # 조류 위험도 등급 변화 이력
                self.request_bird_log(start_time, end_time)
            elif log_type_index == 2:  # 조종사 요청 응답 이력
                self.request_pilot_log(start_time, end_time)
            else:
                logger.warning(f"알 수 없는 로그 타입 인덱스: {log_type_index}")
                
        except Exception as e:
            logger.error(f"검색 요청 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"검색 요청 처리 중 오류가 발생했습니다: {e}")

    def request_object_log(self, start_time: str, end_time: str):
        """객체 감지 이력 조회 요청 (LC_OL)"""
        try:
            tcp_client = self.network_manager.tcp_client
            if tcp_client:
                message = f"{MessagePrefix.LC_OL.value}:{start_time},{end_time}"
                tcp_client._send_command(message, "객체 감지 로그 조회 요청")
                logger.info(f"객체 감지 이력 조회 요청 전송: {message}")
            else:
                logger.error("TCP 클라이언트가 없습니다")
                QMessageBox.warning(self, "오류", "TCP 연결이 설정되지 않았습니다.")
        except Exception as e:
            logger.error(f"객체 감지 이력 요청 오류: {e}")
            QMessageBox.critical(self, "오류", f"객체 감지 로그 요청 중 오류가 발생했습니다: {e}")

    def request_bird_log(self, start_time: str, end_time: str):
        """조류 위험도 등급 변화 이력 조회 요청 (LC_BL)"""
        try:
            tcp_client = self.network_manager.tcp_client
            if tcp_client:
                message = f"{MessagePrefix.LC_BL.value}:{start_time},{end_time}"
                tcp_client._send_command(message, "조류 위험도 로그 조회 요청")
                logger.info(f"조류 위험도 등급 변화 이력 조회 요청 전송: {message}")
            else:
                logger.error("TCP 클라이언트가 없습니다")
                QMessageBox.warning(self, "오류", "TCP 연결이 설정되지 않았습니다.")
        except Exception as e:
            logger.error(f"조류 위험도 등급 변화 이력 요청 오류: {e}")
            QMessageBox.critical(self, "오류", f"조류 위험도 로그 요청 중 오류가 발생했습니다: {e}")

    def request_pilot_log(self, start_time: str, end_time: str):
        """조종사 요청 응답 이력 조회 요청 (LC_RL)"""
        try:
            tcp_client = self.network_manager.tcp_client
            if tcp_client:
                message = f"{MessagePrefix.LC_RL.value}:{start_time},{end_time}"
                tcp_client._send_command(message, "파일럿 로그 조회 요청")
                logger.info(f"조종사 요청 응답 이력 조회 요청 전송: {message}")
            else:
                logger.error("TCP 클라이언트가 없습니다")
                QMessageBox.warning(self, "오류", "TCP 연결이 설정되지 않았습니다.")
        except Exception as e:
            logger.error(f"조종사 요청 응답 이력 요청 오류: {e}")
            QMessageBox.critical(self, "오류", f"조종사 로그 요청 중 오류가 발생했습니다: {e}")

    def on_object_detection_log_received(self, detection_logs: list):
        """객체 감지 로그 응답 수신 처리"""
        try:
            logger.info(f"객체 감지 로그 데이터 수신: {len(detection_logs)}건")
            
            if not hasattr(self, 'tableWidget_object'):
                logger.error("tableWidget_object가 존재하지 않습니다")
                return
            
            # 원본 데이터 저장 (필터링용)
            self.original_object_data = detection_logs
            
            # 로그 데이터가 없는 경우
            if not detection_logs:
                QMessageBox.information(self, "검색 결과", "해당 기간의 객체 감지 로그가 없습니다.")
                return
            
            # 테이블에 데이터 표시
            self.display_object_detection_data(detection_logs)
            
            # 객체 감지 로그 페이지로 전환
            self.stackedWidget.setCurrentIndex(0)
            
            logger.info(f"객체 감지 로그 테이블 업데이트 완료: {len(detection_logs)}건")
            
        except Exception as e:
            logger.error(f"객체 감지 로그 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"객체 감지 로그 처리 중 오류가 발생했습니다: {e}")

    def display_object_detection_data(self, detection_logs: list):
        """객체 감지 데이터를 테이블에 표시"""
        try:
            # 테이블 초기화
            self.tableWidget_object.setRowCount(0)
            
            if not detection_logs:
                return
            
            # 테이블에 데이터 추가
            self.tableWidget_object.setRowCount(len(detection_logs))
            successful_rows = 0
            
            for row, detection_log in enumerate(detection_logs):
                try:
                    # No.
                    no_item = QTableWidgetItem(str(row + 1))
                    self.tableWidget_object.setItem(row, 0, no_item)
                    
                    # 객체 ID
                    id_item = QTableWidgetItem(str(detection_log.object_id))
                    self.tableWidget_object.setItem(row, 1, id_item)
                    
                    # 객체 종류
                    type_item = QTableWidgetItem(detection_log.object_type.value)
                    self.tableWidget_object.setItem(row, 2, type_item)
                    
                    # 구역
                    area_item = QTableWidgetItem(detection_log.area.value)
                    self.tableWidget_object.setItem(row, 3, area_item)
                    
                    # 시간
                    time_str = detection_log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if detection_log.timestamp else "N/A"
                    time_item = QTableWidgetItem(time_str)
                    self.tableWidget_object.setItem(row, 4, time_item)
                    
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"객체 감지 로그 행 {row} 처리 오류: {e}")
                    # 오류가 있는 행은 기본값으로 표시
                    try:
                        no_item = QTableWidgetItem(str(row + 1))
                        self.tableWidget_object.setItem(row, 0, no_item)
                        id_item = QTableWidgetItem("0")
                        self.tableWidget_object.setItem(row, 1, id_item)
                        type_item = QTableWidgetItem("파싱 오류")
                        self.tableWidget_object.setItem(row, 2, type_item)
                        area_item = QTableWidgetItem("N/A")
                        self.tableWidget_object.setItem(row, 3, area_item)
                        time_item = QTableWidgetItem("N/A")
                        self.tableWidget_object.setItem(row, 4, time_item)
                    except:
                        pass
                    continue
            
            if successful_rows < len(detection_logs):
                logger.warning(f"객체 감지 로그 일부 처리 실패: 성공 {successful_rows}개/{len(detection_logs)}개")
                    
        except Exception as e:
            logger.error(f"객체 감지 데이터 표시 오류: {e}")

    def on_object_detection_log_error(self, error_message: str):
        """객체 감지 로그 오류 처리"""
        logger.error(f"객체 감지 로그 오류: {error_message}")
        # 파싱 오류인 경우 기술적 세부사항 숨기고 사용자 친화적 메시지 표시
        if "파싱" in error_message or "parsing" in error_message.lower():
            user_message = "서버 응답 형식에 문제가 있습니다. 잠시 후 다시 시도해주세요."
        else:
            user_message = error_message
        QMessageBox.critical(self, "객체 감지 로그 오류", f"객체 감지 로그 조회 중 오류가 발생했습니다:\n{user_message}")

    def on_bird_risk_log_received(self, bird_risk_logs: list):
        """조류 위험도 로그 응답 수신 처리"""
        try:
            logger.info(f"조류 위험도 로그 데이터 수신: {len(bird_risk_logs)}건")
            
            if not hasattr(self, 'tableWidget_bird'):
                logger.error("tableWidget_bird가 존재하지 않습니다")
                return
            
            # 테이블 초기화
            self.tableWidget_bird.setRowCount(0)
            
            # 로그 데이터가 없는 경우
            if not bird_risk_logs:
                QMessageBox.information(self, "검색 결과", "해당 기간의 조류 위험도 변화 로그가 없습니다.")
                return
            
            # 테이블에 데이터 추가
            self.tableWidget_bird.setRowCount(len(bird_risk_logs))
            successful_rows = 0
            
            for row, bird_risk_log in enumerate(bird_risk_logs):
                try:
                    # No.
                    no_item = QTableWidgetItem(str(row + 1))
                    self.tableWidget_bird.setItem(row, 0, no_item)
                    
                    # 조류 위험도
                    risk_item = QTableWidgetItem(bird_risk_log.bird_risk_level.value)
                    self.tableWidget_bird.setItem(row, 1, risk_item)
                    
                    # 시간
                    time_str = bird_risk_log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if bird_risk_log.timestamp else "N/A"
                    time_item = QTableWidgetItem(time_str)
                    self.tableWidget_bird.setItem(row, 2, time_item)
                    
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"조류 위험도 로그 행 {row} 처리 오류: {e}")
                    # 오류가 있는 행은 기본값으로 표시
                    try:
                        no_item = QTableWidgetItem(str(row + 1))
                        self.tableWidget_bird.setItem(row, 0, no_item)
                        error_item = QTableWidgetItem("파싱 오류")
                        self.tableWidget_bird.setItem(row, 1, error_item)
                        time_item = QTableWidgetItem("N/A")
                        self.tableWidget_bird.setItem(row, 2, time_item)
                    except:
                        pass
                    continue
            
            # 조류 위험도 로그 페이지로 전환
            self.stackedWidget.setCurrentIndex(1)
            
            if successful_rows < len(bird_risk_logs):
                logger.warning(f"조류 위험도 로그 일부 처리 실패: 성공 {successful_rows}개/{len(bird_risk_logs)}개")
            
            logger.info(f"조류 위험도 로그 테이블 업데이트 완료: 성공 {successful_rows}개/{len(bird_risk_logs)}개")
            
        except Exception as e:
            logger.error(f"조류 위험도 로그 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"조류 위험도 로그 처리 중 오류가 발생했습니다: {e}")

    def on_bird_risk_log_error(self, error_message: str):
        """조류 위험도 로그 오류 처리"""
        logger.error(f"조류 위험도 로그 오류: {error_message}")
        # 파싱 오류인 경우 기술적 세부사항 숨기고 사용자 친화적 메시지 표시
        if "파싱" in error_message or "parsing" in error_message.lower():
            user_message = "서버 응답 형식에 문제가 있습니다. 잠시 후 다시 시도해주세요."
        else:
            user_message = error_message
        QMessageBox.critical(self, "조류 위험도 로그 오류", f"조류 위험도 로그 조회 중 오류가 발생했습니다:\n{user_message}")

    def on_pilot_log_received(self, pilot_logs: list):
        """파일럿 로그 응답 수신 처리"""
        try:
            logger.info(f"파일럿 로그 데이터 수신: {len(pilot_logs)}건")
            
            if not hasattr(self, 'tableWidget_pilot'):
                logger.error("tableWidget_pilot이 존재하지 않습니다")
                return
            
            # 테이블 초기화
            self.tableWidget_pilot.setRowCount(0)
            
            # 로그 데이터가 없는 경우
            if not pilot_logs:
                QMessageBox.information(self, "검색 결과", "해당 기간의 조종사 로그가 없습니다.")
                return
            
            # 테이블에 데이터 추가
            self.tableWidget_pilot.setRowCount(len(pilot_logs))
            successful_rows = 0
            
            for row, pilot_log in enumerate(pilot_logs):
                try:
                    # No.
                    no_item = QTableWidgetItem(str(row + 1))
                    self.tableWidget_pilot.setItem(row, 0, no_item)
                    
                    # 요청 타입
                    request_item = QTableWidgetItem(pilot_log.request_type.value)
                    self.tableWidget_pilot.setItem(row, 1, request_item)
                    
                    # 응답 타입
                    response_item = QTableWidgetItem(pilot_log.response_type.value)
                    self.tableWidget_pilot.setItem(row, 2, response_item)
                    
                    # 요청 시간
                    request_time = pilot_log.request_timestamp.strftime("%Y-%m-%d %H:%M:%S") if pilot_log.request_timestamp else "N/A"
                    request_time_item = QTableWidgetItem(request_time)
                    self.tableWidget_pilot.setItem(row, 3, request_time_item)
                    
                    # 응답 시간
                    response_time = pilot_log.response_timestamp.strftime("%Y-%m-%d %H:%M:%S") if pilot_log.response_timestamp else "N/A"
                    response_time_item = QTableWidgetItem(response_time)
                    self.tableWidget_pilot.setItem(row, 4, response_time_item)
                    
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"파일럿 로그 행 {row} 처리 오류: {e}")
                    # 오류가 있는 행은 기본값으로 표시
                    try:
                        no_item = QTableWidgetItem(str(row + 1))
                        self.tableWidget_pilot.setItem(row, 0, no_item)
                        request_item = QTableWidgetItem("파싱 오류")
                        self.tableWidget_pilot.setItem(row, 1, request_item)
                        response_item = QTableWidgetItem("파싱 오류")
                        self.tableWidget_pilot.setItem(row, 2, response_item)
                        request_time_item = QTableWidgetItem("N/A")
                        self.tableWidget_pilot.setItem(row, 3, request_time_item)
                        response_time_item = QTableWidgetItem("N/A")
                        self.tableWidget_pilot.setItem(row, 4, response_time_item)
                    except:
                        pass
                    continue
            
            # 조종사 로그 페이지로 전환
            self.stackedWidget.setCurrentIndex(2)
            
            if successful_rows < len(pilot_logs):
                logger.warning(f"파일럿 로그 일부 처리 실패: 성공 {successful_rows}개/{len(pilot_logs)}개")
            
            logger.info(f"파일럿 로그 테이블 업데이트 완료: 성공 {successful_rows}개/{len(pilot_logs)}개")
            
        except Exception as e:
            logger.error(f"파일럿 로그 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"파일럿 로그 처리 중 오류가 발생했습니다: {e}")

    def on_pilot_log_error(self, error_message: str):
        """파일럿 로그 오류 처리"""
        logger.error(f"파일럿 로그 오류: {error_message}")
        # 파싱 오류인 경우 기술적 세부사항 숨기고 사용자 친화적 메시지 표시
        if "파싱" in error_message or "parsing" in error_message.lower():
            user_message = "서버 응답 형식에 문제가 있습니다. 잠시 후 다시 시도해주세요."
        else:
            user_message = error_message
        QMessageBox.critical(self, "파일럿 로그 오류", f"파일럿 로그 조회 중 오류가 발생했습니다:\n{user_message}")

    def request_current_settings(self):
        """Log 탭 활성화 시 호출되는 메서드 - 현재 설정 초기화"""
        try:            
            # 현재 선택된 로그 타입에 따라 테이블 초기화
            current_index = self.combo_log.currentIndex()
            self.initialize_current_table(current_index)
            
            # 페이지 전환
            self.stackedWidget.setCurrentIndex(current_index)
            
        except Exception as e:
            logger.error(f"Log 페이지 설정 요청 오류: {e}")

    def refresh_current_view(self):
        """현재 선택된 뷰를 새로고침"""
        try:
            current_index = self.combo_log.currentIndex()
            logger.info(f"현재 뷰 새로고침: 인덱스 {current_index}")
            
            # 현재 테이블 초기화
            self.initialize_current_table(current_index)
            
            # 페이지 전환 (필요한 경우)
            if self.stackedWidget.currentIndex() != current_index:
                self.stackedWidget.setCurrentIndex(current_index)
                
        except Exception as e:
            logger.error(f"뷰 새로고침 오류: {e}")

    def clear_all_tables(self):
        """모든 테이블 데이터 지우기"""
        try:
            tables = [
                ('tableWidget_object', '객체 감지'),
                ('tableWidget_bird', '조류 위험도'),
                ('tableWidget_pilot', '파일럿 로그')
            ]
            
            for table_name, table_desc in tables:
                if hasattr(self, table_name):
                    table = getattr(self, table_name)
                    table.setRowCount(0)
                    logger.debug(f"{table_desc} 테이블 데이터 삭제")
                    
            logger.info("모든 테이블 데이터 삭제 완료")
            
        except Exception as e:
            logger.error(f"테이블 데이터 삭제 오류: {e}")

    def get_current_log_type(self):
        """현재 선택된 로그 타입 반환"""
        try:
            current_index = self.combo_log.currentIndex()
            current_text = self.combo_log.currentText()
            
            log_types = {
                0: "object_detection",
                1: "bird_risk",
                2: "pilot_log"
            }
            
            return {
                'index': current_index,
                'text': current_text,
                'type': log_types.get(current_index, "unknown")
            }
            
        except Exception as e:
            logger.error(f"현재 로그 타입 확인 오류: {e}")
            return {'index': 0, 'text': '위험요소 감지 이력', 'type': 'object_detection'}

    def on_show_image_clicked(self):
        """이미지 보기 버튼 클릭 처리"""
        try:
            # 현재 선택된 로그 타입이 객체 감지 이력인지 확인
            if self.combo_log.currentIndex() != 0:
                QMessageBox.information(self, "알림", "이미지 보기는 위험요소 감지 이력에서만 사용할 수 있습니다.")
                return
            
            # 객체 감지 테이블에서 선택된 행 확인
            if not hasattr(self, 'tableWidget_object'):
                QMessageBox.warning(self, "오류", "객체 감지 테이블이 초기화되지 않았습니다.")
                return
            
            selected_row = self.tableWidget_object.currentRow()
            if selected_row < 0:
                QMessageBox.information(self, "알림", "이미지를 보려는 객체를 테이블에서 선택해주세요.")
                return
            
            # 선택된 행에서 객체 ID 추출
            object_id_item = self.tableWidget_object.item(selected_row, 1)  # 객체 ID는 1번 컬럼
            if not object_id_item:
                QMessageBox.warning(self, "오류", "선택된 행에서 객체 ID를 찾을 수 없습니다.")
                return
            
            try:
                object_id = int(object_id_item.text())
            except ValueError:
                QMessageBox.warning(self, "오류", "유효하지 않은 객체 ID입니다.")
                return
            
            # LC_OI 명령 전송
            self.request_object_image(object_id)
            
        except Exception as e:
            logger.error(f"이미지 보기 버튼 클릭 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"이미지 요청 처리 중 오류가 발생했습니다: {e}")

    def request_object_image(self, object_id: int):
        """객체 이미지 조회 요청 (LC_OI)"""
        try:
            tcp_client = self.network_manager.tcp_client
            if not tcp_client:
                QMessageBox.warning(self, "오류", "TCP 연결이 설정되지 않았습니다.")
                return
            
            if not tcp_client.is_connected():
                QMessageBox.warning(self, "오류", "서버에 연결되어 있지 않습니다.")
                return
            
            # 로그 페이지 전용 객체 이미지 요청 메서드 사용
            result = tcp_client.request_log_object_image(object_id)
            if result:
                logger.info(f"로그 페이지 객체 이미지 조회 요청 전송 성공: ID={object_id}")
            else:
                logger.error(f"로그 페이지 객체 이미지 조회 요청 전송 실패: ID={object_id}")
                QMessageBox.warning(self, "오류", "이미지 요청 전송에 실패했습니다.")

        except Exception as e:
            logger.error(f"객체 이미지 조회 요청 오류: {e}")
            QMessageBox.critical(self, "오류", f"객체 이미지 요청 중 오류가 발생했습니다: {e}")

    def on_object_image_received(self, detected_object):
        """객체 이미지 응답 수신 처리"""
        try:
            logger.info(f"객체 이미지 수신: ID {detected_object.object_id}")
            
            # 이미지 데이터가 있는지 확인
            if not detected_object.image_data:
                QMessageBox.information(self, "이미지 없음", f"객체 ID {detected_object.object_id}의 이미지가 없습니다.")
                return
            
            # 이미지 표시 다이얼로그 생성 및 표시
            self.show_object_image_dialog(detected_object)
            
        except Exception as e:
            logger.error(f"객체 이미지 수신 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"이미지 표시 중 오류가 발생했습니다: {e}")

    def on_object_image_error(self, error_message: str):
        """객체 이미지 오류 처리"""
        logger.error(f"객체 이미지 오류: {error_message}")
        QMessageBox.critical(self, "이미지 요청 오류", f"객체 이미지 조회 중 오류가 발생했습니다:\n{error_message}")

    def show_object_image_dialog(self, detected_object):
        """객체 이미지 표시 다이얼로그"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt
            
            # 다이얼로그 생성
            dialog = QDialog(self)
            dialog.setWindowTitle("객체 이미지")
            dialog.setModal(True)
            dialog.resize(600, 500)
            
            # 레이아웃 설정
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # 이미지 표시 라벨
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("background-color: white;")
            
            # 이미지 데이터를 QPixmap으로 변환 (ObjectDetailDialog와 동일한 방식)
            try:
                pixmap = QPixmap()
                pixmap.loadFromData(detected_object.image_data)
                scaled_pixmap = pixmap.scaled(580, 470, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
                
            except Exception as img_error:
                logger.error(f"이미지 변환 오류: {img_error}")
                image_label.setText("이미지를 표시할 수 없습니다")
            
            layout.addWidget(image_label)
            
            # 다이얼로그 표시
            dialog.exec()
            
        except Exception as e:
            logger.error(f"이미지 다이얼로그 표시 오류: {e}")
            QMessageBox.critical(self, "오류", f"이미지 표시 중 오류가 발생했습니다: {e}")

    def on_filter_apply_clicked(self):
        """필터 적용 버튼 클릭 처리 (객체 감지 데이터만)"""
        try:
            # 현재 선택된 로그 타입 확인
            current_index = self.combo_log.currentIndex()
            
            if current_index == 0:  # 객체 감지 이력
                self.apply_object_filter()
            else:
                QMessageBox.information(self, "알림", "필터링은 위험요소 감지 이력에서만 사용할 수 있습니다.")
                
        except Exception as e:
            logger.error(f"필터 적용 오류: {e}")
            QMessageBox.critical(self, "오류", f"필터 적용 중 오류가 발생했습니다: {e}")

    def apply_object_filter(self):
        """객체 감지 로그 필터 적용"""
        try:
            if not self.original_object_data:
                QMessageBox.information(self, "알림", "필터를 적용할 데이터가 없습니다. 먼저 데이터를 조회해주세요.")
                return
            
            # 필터 조건 가져오기
            selected_area = self.combo_filter_area.currentText() if hasattr(self, 'combo_filter_area') else "전체"
            selected_type = self.combo_filter_type.currentText() if hasattr(self, 'combo_filter_type') else "전체"
            
            logger.info(f"객체 감지 필터 적용: 구역={selected_area}, 종류={selected_type}")
            
            # 필터링된 데이터 생성
            filtered_data = []
            for log in self.original_object_data:
                # 구역 필터
                area_match = (selected_area == "전체" or log.area.value == selected_area)
                # 종류 필터
                type_match = (selected_type == "전체" or log.object_type.value == selected_type)
                
                if area_match and type_match:
                    filtered_data.append(log)
            
            # 필터링된 데이터 표시
            self.display_object_detection_data(filtered_data)
            
            # 결과 메시지
            original_count = len(self.original_object_data)
            filtered_count = len(filtered_data)
            QMessageBox.information(self, "필터 적용", 
                                    f"필터 적용 완료\n전체: {original_count}건 → 필터링 후: {filtered_count}건")
            
        except Exception as e:
            logger.error(f"객체 감지 로그 필터 적용 오류: {e}")
            QMessageBox.critical(self, "오류", f"필터 적용 중 오류가 발생했습니다: {e}")

    def clear_object_filter(self):
        """객체 감지 필터 초기화 (원본 데이터 유지)"""
        try:
            # 필터 콤보박스를 첫 번째 항목("전체")으로 리셋
            if hasattr(self, 'combo_filter_area'):
                self.combo_filter_area.setCurrentIndex(0)
            if hasattr(self, 'combo_filter_type'):
                self.combo_filter_type.setCurrentIndex(0)
                
            # 원본 객체 감지 데이터로 테이블 복원 (데이터가 있는 경우에만)
            if self.original_object_data:
                self.display_object_detection_data(self.original_object_data)
                logger.info(f"객체 감지 필터 초기화 및 원본 데이터 복원: {len(self.original_object_data)}건")
            else:
                logger.info("원본 데이터가 없어 필터만 초기화")
                
        except Exception as e:
            logger.error(f"객체 감지 필터 초기화 오류: {e}")

    def on_reset_clicked(self):
        """리셋 버튼 클릭 처리"""
        try:
            # 현재 선택된 로그 타입 확인
            current_index = self.combo_log.currentIndex()
            
            if current_index == 0:  # 객체 감지 이력에서 리셋
                # 필터만 초기화하고 원본 데이터는 유지
                self.reset_object_filter_only()
            else:
                # 다른 로그 타입에서는 전체 리셋
                self.full_reset()
            
            logger.info("로그 페이지 리셋 완료")
            
        except Exception as e:
            logger.error(f"리셋 처리 오류: {e}")
            QMessageBox.critical(self, "오류", f"리셋 처리 중 오류가 발생했습니다: {e}")
    
    def reset_object_filter_only(self):
        """객체 감지 로그에서 필터만 초기화 (데이터는 유지)"""
        try:
            # 필터 콤보박스를 첫 번째 항목("전체")으로 리셋
            if hasattr(self, 'combo_filter_area'):
                self.combo_filter_area.setCurrentIndex(0)
            if hasattr(self, 'combo_filter_type'):
                self.combo_filter_type.setCurrentIndex(0)
                
            # 원본 객체 감지 데이터로 테이블 복원 (데이터가 있는 경우에만)
            if self.original_object_data:
                self.display_object_detection_data(self.original_object_data)
                logger.info(f"원본 객체 감지 데이터 복원: {len(self.original_object_data)}건")
            else:
                # 원본 데이터가 없으면 테이블만 초기화
                self.tableWidget_object.setRowCount(0)
                logger.info("원본 데이터가 없어 테이블만 초기화")
                
        except Exception as e:
            logger.error(f"객체 필터 초기화 오류: {e}")
    
    def full_reset(self):
        """전체 리셋 (날짜, 콤보박스, 모든 데이터)"""
        try:
            # 날짜를 기본값으로 리셋
            today = QDate.currentDate()
            self.start_date.setDate(today.addDays(-30))  # 30일 전
            self.end_date.setDate(today)  # 오늘
            
            # 콤보박스를 첫 번째 항목으로 리셋
            self.combo_log.setCurrentIndex(0)
            
            # 객체 감지 필터 초기화
            self.clear_object_filter()
            
            # 원본 객체 감지 데이터 초기화
            self.original_object_data = []
            
            # 모든 테이블 데이터 삭제
            self.clear_all_tables()
            
            # 첫 번째 페이지로 이동
            self.stackedWidget.setCurrentIndex(0)
            
            # 첫 번째 테이블 초기화
            self.initialize_current_table(0)
            
            logger.info("전체 리셋 완료")
            
        except Exception as e:
            logger.error(f"전체 리셋 오류: {e}")
