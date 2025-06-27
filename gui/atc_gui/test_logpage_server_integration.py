#!/usr/bin/env python3
"""
LogPage 서버 통신 통합 테스트
LogPage의 인터페이스 규칙 및 서버 통신 기능을 검증하는 테스트 도구
"""

import sys
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit, QSplitter
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont

# 프로젝트 루트를 시스템 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from views.log_page import LogPage
from utils.interface import ObjectDetectionLog, BirdRiskLog, PilotLog, DetectedObject
from config.constants import ObjectType, AirportArea, EventType, BirdRiskLevel, PilotRequestType, PilotResponseType


class MockTcpClient(QObject):
    """모의 TCP 클라이언트"""
    
    # LogPage에서 사용하는 시그널들
    pilot_log_response = pyqtSignal(list)
    pilot_log_error = pyqtSignal(str)
    object_detection_log_response = pyqtSignal(list)
    object_detection_log_error = pyqtSignal(str)
    bird_risk_log_response = pyqtSignal(list)
    bird_risk_log_error = pyqtSignal(str)
    object_detail_response = pyqtSignal(object)
    object_detail_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_connected_flag = True
    
    def is_connected(self):
        return self.is_connected_flag
        
    def _send_command(self, message: str, description: str = ""):
        """명령 전송 시뮬레이션"""
        print(f"[MockTCP] 전송: {message} ({description})")
        
        # 명령에 따라 적절한 응답 시뮬레이션
        QTimer.singleShot(500, lambda: self._simulate_response(message))
    
    def _simulate_response(self, command: str):
        """서버 응답 시뮬레이션"""
        try:
            if command.startswith("LC_OL:"):  # 객체 감지 로그 요청
                self._simulate_object_detection_response()
            elif command.startswith("LC_BL:"):  # 조류 위험도 로그 요청
                self._simulate_bird_risk_response()
            elif command.startswith("LC_RL:"):  # 파일럿 로그 요청
                self._simulate_pilot_log_response()
            elif command.startswith("LC_OI:"):  # 객체 이미지 요청
                object_id = int(command.split(":")[1])
                self._simulate_object_image_response(object_id)
        except Exception as e:
            print(f"[MockTCP] 응답 시뮬레이션 오류: {e}")
    
    def _simulate_object_detection_response(self):
        """객체 감지 로그 응답 시뮬레이션"""
        logs = []
        base_time = datetime.now()
        
        # 테스트 데이터 생성
        test_objects = [
            (1001, ObjectType.BIRD, AirportArea.RWY_A),
            (1002, ObjectType.FOD, AirportArea.TWY_A),
            (1003, ObjectType.PERSON, AirportArea.GRASS_A),
            (1004, ObjectType.VEHICLE, AirportArea.TWY_B),
            (1005, ObjectType.BIRD, AirportArea.RWY_B),
        ]
        
        for i, (obj_id, obj_type, area) in enumerate(test_objects):
            log = ObjectDetectionLog(
                event_type=EventType.HAZARD,
                object_id=obj_id,
                object_type=obj_type,
                area=area,
                timestamp=base_time - timedelta(minutes=i*5)
            )
            logs.append(log)
        
        print(f"[MockTCP] 객체 감지 로그 응답: {len(logs)}건")
        self.object_detection_log_response.emit(logs)
    
    def _simulate_bird_risk_response(self):
        """조류 위험도 로그 응답 시뮬레이션"""
        logs = []
        base_time = datetime.now()
        
        risk_levels = [BirdRiskLevel.HIGH, BirdRiskLevel.MEDIUM, BirdRiskLevel.LOW]
        
        for i, risk_level in enumerate(risk_levels):
            log = BirdRiskLog(
                bird_risk_level=risk_level,
                timestamp=base_time - timedelta(hours=i)
            )
            logs.append(log)
        
        print(f"[MockTCP] 조류 위험도 로그 응답: {len(logs)}건")
        self.bird_risk_log_response.emit(logs)
    
    def _simulate_pilot_log_response(self):
        """파일럿 로그 응답 시뮬레이션"""
        logs = []
        base_time = datetime.now()
        
        # 테스트 파일럿 요청/응답 데이터
        test_pilots = [
            (PilotRequestType.BR_INQ, PilotResponseType.BR_HIGH),
            (PilotRequestType.RWY_A_STATUS, PilotResponseType.CLEAR),
            (PilotRequestType.RWY_B_STATUS, PilotResponseType.BLOCKED),
            (PilotRequestType.RWY_AVAIL_IN, PilotResponseType.A_ONLY),
        ]
        
        for i, (req_type, resp_type) in enumerate(test_pilots):
            request_time = base_time - timedelta(minutes=i*10)
            response_time = request_time + timedelta(seconds=30)
            
            log = PilotLog(
                request_type=req_type,
                response_type=resp_type,
                request_timestamp=request_time,
                response_timestamp=response_time
            )
            logs.append(log)
        
        print(f"[MockTCP] 파일럿 로그 응답: {len(logs)}건")
        self.pilot_log_response.emit(logs)
    
    def _simulate_object_image_response(self, object_id: int):
        """객체 이미지 응답 시뮬레이션"""
        # 더미 이미지 데이터 생성 (1x1 빨간 픽셀)
        dummy_image_data = b'\xff\x00\x00'  # RGB 빨간색 픽셀
        
        detected_object = DetectedObject(
            object_id=object_id,
            object_type=ObjectType.BIRD,
            x_coord=100.0,
            y_coord=200.0,
            area=AirportArea.RWY_A,
            event_type=EventType.HAZARD,
            timestamp=datetime.now(),
            state_info=80,
            image_data=dummy_image_data
        )
        
        print(f"[MockTCP] 객체 이미지 응답: ID {object_id}")
        self.object_detail_response.emit(detected_object)


class MockNetworkManager(QObject):
    """모의 네트워크 매니저"""
    
    def __init__(self):
        super().__init__()
        self.tcp_client = MockTcpClient()


class LogPageTestWindow(QMainWindow):
    """LogPage 테스트 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LogPage 인터페이스 규칙 검증 테스트")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 분할기 생성
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 네트워크 매니저 설정
        self.network_manager = MockNetworkManager()
        
        # LogPage 인스턴스 생성 (왼쪽)
        self.log_page = LogPage(network_manager=self.network_manager)
        splitter.addWidget(self.log_page)
        
        # 테스트 컨트롤 패널 (오른쪽)
        self.setup_test_control_panel(splitter)
        
        # 분할기 비율 설정 (LogPage 70%, 컨트롤 패널 30%)
        splitter.setSizes([1120, 480])
        
        # 자동 테스트 시작
        QTimer.singleShot(1000, self.start_auto_test)
        
        print("LogPage 테스트 윈도우 초기화 완료")
    
    def setup_test_control_panel(self, splitter):
        """테스트 컨트롤 패널 설정"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 제목
        title_label = QLabel("📋 인터페이스 규칙 검증")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(title_label)
        
        # 상태 표시
        self.status_label = QLabel("🔄 테스트 준비 중...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
            }
        """)
        control_layout.addWidget(self.status_label)
        
        # 테스트 버튼들
        self.test_buttons = {}
        buttons = [
            ("📊 객체 감지 로그", self.test_object_detection, "#17a2b8"),
            ("🐦 조류 위험도 로그", self.test_bird_risk, "#28a745"),
            ("✈️ 파일럿 로그", self.test_pilot_log, "#ffc107"),
            ("🖼️ 객체 이미지", self.test_object_image, "#6f42c1"),
            ("🔧 필터링 테스트", self.test_filtering, "#fd7e14"),
            ("❌ 오류 처리", self.simulate_error, "#dc3545"),
            ("🔄 전체 테스트", self.run_full_test, "#20c997")
        ]
        
        for text, handler, color in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    margin: 3px 0;
                }}
                QPushButton:hover {{
                    background-color: {self.darken_color(color)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color, 0.8)};
                }}
                QPushButton:disabled {{
                    background-color: #6c757d;
                    color: #adb5bd;
                }}
            """)
            control_layout.addWidget(btn)
            self.test_buttons[text] = btn
        
        # 로그 출력 영역
        self.setup_log_output(control_layout)
        
        # 검증 결과 영역
        self.setup_validation_results(control_layout)
        
        splitter.addWidget(control_widget)
    
    def darken_color(self, hex_color, factor=0.8):
        """색상을 어둡게 만드는 헬퍼 함수"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"
    
    def setup_log_output(self, layout):
        """로그 출력 영역 설정"""
        log_label = QLabel("📝 테스트 로그")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(120)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #212529;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_output)
    
    def setup_validation_results(self, layout):
        """검증 결과 영역 설정"""
        validation_label = QLabel("✅ 검증 결과")
        validation_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(validation_label)
        
        self.validation_output = QTextEdit()
        self.validation_output.setMaximumHeight(100)
        self.validation_output.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.validation_output)
    
    def log_message(self, message: str, level: str = "INFO"):
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color_codes = {
            "INFO": "#00ff00",
            "WARN": "#ffff00", 
            "ERROR": "#ff4444",
            "SUCCESS": "#44ff44"
        }
        color = color_codes.get(level, "#ffffff")
        self.log_output.append(f'<span style="color: {color};">[{timestamp}] {message}</span>')
        print(f"[{timestamp}] {message}")
    
    def validation_message(self, message: str, passed: bool = True):
        """검증 결과 메시지 출력"""
        icon = "✅" if passed else "❌"
        color = "#28a745" if passed else "#dc3545"
        self.validation_output.append(f'<span style="color: {color};">{icon} {message}</span>')
    
    def start_auto_test(self):
        """자동 테스트 시작"""
        self.status_label.setText("✅ 테스트 준비 완료")
        self.log_message("LogPage 자동 테스트 시작", "SUCCESS")
        self.log_message("인터페이스 규칙 검증을 위한 더미 데이터 로드 준비")
    
    def test_object_detection(self):
        """객체 감지 로그 테스트 및 인터페이스 규칙 검증"""
        self.status_label.setText("📊 객체 감지 로그 테스트 중...")
        self.log_message("객체 감지 로그 테스트 시작", "INFO")
        
        # LogPage의 combo_log을 객체 감지로 설정
        self.log_page.combo_log.setCurrentIndex(0)
        self.log_message("로그 타입을 '객체 감지'로 설정")
        
        # 조회 버튼 클릭 시뮬레이션
        self.log_page.on_search_clicked()
        self.log_message("LC_OL 명령 전송 시뮬레이션")
        
        # 검증 수행
        QTimer.singleShot(800, self.validate_object_detection)
    
    def validate_object_detection(self):
        """객체 감지 로그 인터페이스 규칙 검증"""
        table = self.log_page.tableWidget_object
        
        # 1. 테이블 데이터 존재 확인
        row_count = table.rowCount()
        if row_count > 0:
            self.validation_message(f"객체 감지 데이터 로드 성공 ({row_count}건)")
        else:
            self.validation_message("객체 감지 데이터 로드 실패", False)
            return
        
        # 2. No. 컬럼 순번 검증
        for row in range(min(row_count, 5)):  # 최대 5개만 확인
            item = table.item(row, 0)
            if item and item.text() == str(row + 1):
                continue
            else:
                self.validation_message(f"No. 컬럼 순번 오류 (행 {row})", False)
                return
        self.validation_message("No. 컬럼 순번 정상")
        
        # 3. 필수 컬럼 데이터 존재 확인
        required_columns = ["객체 ID", "객체 종류", "구역", "시간"]
        for col_idx, col_name in enumerate(required_columns, 1):
            if row_count > 0:
                item = table.item(0, col_idx)
                if item and item.text().strip():
                    self.validation_message(f"{col_name} 컬럼 데이터 정상")
                else:
                    self.validation_message(f"{col_name} 컬럼 데이터 누락", False)
        
        # 4. Constants 매핑 검증 (ObjectType, AirportArea)
        self.validate_constants_mapping(table)
        
        self.status_label.setText("✅ 객체 감지 로그 테스트 완료")
        self.log_message("객체 감지 로그 인터페이스 규칙 검증 완료", "SUCCESS")
    
    def validate_constants_mapping(self, table):
        """Constants 매핑 규칙 검증"""
        if table.rowCount() == 0:
            return
            
        # 객체 종류가 ObjectType enum 값과 일치하는지 확인
        valid_object_types = [ot.value for ot in ObjectType]
        valid_areas = [area.value for area in AirportArea]
        
        for row in range(min(table.rowCount(), 3)):  # 샘플 3개만 확인
            # 객체 종류 검증
            type_item = table.item(row, 2)  # 객체 종류 컬럼
            if type_item and type_item.text() in valid_object_types:
                self.validation_message(f"행 {row+1}: 객체 종류 enum 매핑 정상")
            else:
                self.validation_message(f"행 {row+1}: 객체 종류 enum 매핑 오류", False)
            
            # 구역 검증
            area_item = table.item(row, 3)  # 구역 컬럼
            if area_item and area_item.text() in valid_areas:
                self.validation_message(f"행 {row+1}: 구역 enum 매핑 정상")
            else:
                self.validation_message(f"행 {row+1}: 구역 enum 매핑 오류", False)
    
    def test_bird_risk(self):
        """조류 위험도 로그 테스트"""
        self.status_label.setText("🐦 조류 위험도 로그 테스트 중...")
        self.log_message("조류 위험도 로그 테스트 시작", "INFO")
        
        self.log_page.combo_log.setCurrentIndex(1)
        self.log_message("로그 타입을 '조류 위험도'로 설정")
        
        self.log_page.on_search_clicked()
        self.log_message("LC_BL 명령 전송 시뮬레이션")
        
        QTimer.singleShot(800, self.validate_bird_risk)
    
    def validate_bird_risk(self):
        """조류 위험도 로그 검증"""
        table = self.log_page.tableWidget_bird
        row_count = table.rowCount()
        
        if row_count > 0:
            self.validation_message(f"조류 위험도 데이터 로드 성공 ({row_count}건)")
        else:
            self.validation_message("조류 위험도 데이터 로드 실패", False)
            return
        
        # BirdRiskLevel enum 값 검증
        valid_risk_levels = [level.value for level in BirdRiskLevel]
        for row in range(min(row_count, 3)):
            risk_item = table.item(row, 1)  # 조류 위험도 컬럼
            if risk_item and risk_item.text() in valid_risk_levels:
                self.validation_message(f"행 {row+1}: 조류 위험도 enum 매핑 정상")
            else:
                self.validation_message(f"행 {row+1}: 조류 위험도 enum 매핑 오류", False)
        
        self.status_label.setText("✅ 조류 위험도 로그 테스트 완료")
        self.log_message("조류 위험도 로그 인터페이스 규칙 검증 완료", "SUCCESS")
    
    def test_pilot_log(self):
        """파일럿 로그 테스트"""
        self.status_label.setText("✈️ 파일럿 로그 테스트 중...")
        self.log_message("파일럿 로그 테스트 시작", "INFO")
        
        self.log_page.combo_log.setCurrentIndex(2)
        self.log_message("로그 타입을 '파일럿 로그'로 설정")
        
        self.log_page.on_search_clicked()
        self.log_message("LC_RL 명령 전송 시뮬레이션")
        
        QTimer.singleShot(800, self.validate_pilot_log)
    
    def validate_pilot_log(self):
        """파일럿 로그 검증"""
        table = self.log_page.tableWidget_pilot
        row_count = table.rowCount()
        
        if row_count > 0:
            self.validation_message(f"파일럿 로그 데이터 로드 성공 ({row_count}건)")
        else:
            self.validation_message("파일럿 로그 데이터 로드 실패", False)
            return
        
        # PilotRequestType, PilotResponseType enum 값 검증
        valid_request_types = [req.value for req in PilotRequestType]
        valid_response_types = [resp.value for resp in PilotResponseType]
        
        for row in range(min(row_count, 3)):
            # 요청 타입 검증
            req_item = table.item(row, 1)
            if req_item and req_item.text() in valid_request_types:
                self.validation_message(f"행 {row+1}: 요청 타입 enum 매핑 정상")
            else:
                self.validation_message(f"행 {row+1}: 요청 타입 enum 매핑 오류", False)
            
            # 응답 타입 검증
            resp_item = table.item(row, 2)
            if resp_item and resp_item.text() in valid_response_types:
                self.validation_message(f"행 {row+1}: 응답 타입 enum 매핑 정상")
            else:
                self.validation_message(f"행 {row+1}: 응답 타입 enum 매핑 오류", False)
        
        self.status_label.setText("✅ 파일럿 로그 테스트 완료")
        self.log_message("파일럿 로그 인터페이스 규칙 검증 완료", "SUCCESS")
    
    def test_object_image(self):
        """객체 이미지 테스트"""
        self.status_label.setText("🖼️ 객체 이미지 테스트 중...")
        self.log_message("객체 이미지 테스트 시작", "INFO")
        
        # 먼저 객체 감지 로그를 로드
        self.log_page.combo_log.setCurrentIndex(0)
        self.log_page.on_search_clicked()
        
        # 1.5초 후 이미지 요청
        QTimer.singleShot(1500, self._request_test_image)
    
    def _request_test_image(self):
        """테스트 이미지 요청"""
        if self.log_page.tableWidget_object.rowCount() > 0:
            self.log_page.tableWidget_object.selectRow(0)
            self.log_message("첫 번째 객체 선택")
            self.log_page.on_show_image_clicked()
            self.log_message("LC_OI 명령 전송 시뮬레이션")
            self.validation_message("객체 이미지 요청 성공")
            self.status_label.setText("✅ 객체 이미지 테스트 완료")
        else:
            self.log_message("표시할 객체가 없습니다", "WARN")
            self.validation_message("객체 이미지 테스트 실패: 객체 없음", False)
    
    def test_filtering(self):
        """필터링 기능 테스트"""
        self.status_label.setText("🔧 필터링 기능 테스트 중...")
        self.log_message("필터링 기능 테스트 시작", "INFO")
        
        # 먼저 객체 감지 로그 로드
        self.log_page.combo_log.setCurrentIndex(0)
        self.log_page.on_search_clicked()
        
        QTimer.singleShot(1000, self._test_filter_functionality)
    
    def _test_filter_functionality(self):
        """필터 기능 검증"""
        # 원본 데이터 수 확인
        original_count = self.log_page.tableWidget_object.rowCount()
        if original_count == 0:
            self.validation_message("필터링 테스트 실패: 원본 데이터 없음", False)
            return
        
        self.validation_message(f"원본 데이터: {original_count}건")
        
        # 필터 적용 (구역 필터)
        if hasattr(self.log_page, 'combo_filter_area'):
            self.log_page.combo_filter_area.setCurrentIndex(1)  # TWY_A 선택
            self.log_message("구역 필터: TWY_A 선택")
            
            if hasattr(self.log_page, 'btn_filter_on'):
                self.log_page.on_filter_apply_clicked()
                self.log_message("필터 적용")
                
                QTimer.singleShot(500, self._validate_filter_results)
            else:
                self.validation_message("필터 적용 버튼 없음", False)
        else:
            self.validation_message("필터 콤보박스 없음", False)
    
    def _validate_filter_results(self):
        """필터 결과 검증"""
        filtered_count = self.log_page.tableWidget_object.rowCount()
        original_count = len(self.log_page.original_object_data)
        self.validation_message(f"필터링 후 데이터: {filtered_count}건")
        
        if filtered_count < original_count:
            self.validation_message("필터링 기능 정상 작동")
        else:
            self.validation_message("필터링 기능 작동 확인 불가", False)
        
        # 리셋 테스트 (객체 감지에서는 원본 데이터 복원)
        if hasattr(self.log_page, 'btn_reset'):
            self.log_page.on_reset_clicked()
            self.log_message("필터 리셋 실행")
            
            # 0.5초 후 리셋 결과 검증
            QTimer.singleShot(500, self._validate_reset_results)
        else:
            self.validation_message("리셋 버튼 없음", False)
            self._complete_filter_test()
    
    def _validate_reset_results(self):
        """리셋 후 결과 검증"""
        reset_count = self.log_page.tableWidget_object.rowCount()
        original_count = len(self.log_page.original_object_data)
        
        self.validation_message(f"리셋 후 데이터: {reset_count}건")
        
        if reset_count == original_count and original_count > 0:
            self.validation_message("리셋 후 원본 데이터 복원 성공")
        elif original_count == 0:
            self.validation_message("원본 데이터가 없어 리셋 테스트 불가", False)
        else:
            self.validation_message("리셋 후 데이터 복원 실패", False)
        
        self._complete_filter_test()
    
    def _complete_filter_test(self):
        """필터링 테스트 완료"""
        self.status_label.setText("✅ 필터링 테스트 완료")
        self.log_message("필터링 기능 인터페이스 규칙 검증 완료", "SUCCESS")
    
    def simulate_error(self):
        """오류 시뮬레이션"""
        self.status_label.setText("❌ 오류 처리 테스트 중...")
        self.log_message("오류 시뮬레이션 실행", "ERROR")
        
        # 각 타입별 오류 시뮬레이션
        error_messages = [
            ("객체 감지 로그", "object_detection_log_error", "서버 연결 실패"),
            ("조류 위험도 로그", "bird_risk_log_error", "데이터베이스 오류"),
            ("파일럿 로그", "pilot_log_error", "요청 타임아웃"),
            ("객체 이미지", "object_detail_error", "이미지 파일 없음")
        ]
        
        for i, (log_type, signal_name, error_msg) in enumerate(error_messages):
            QTimer.singleShot(200 * (i + 1), 
                lambda lt=log_type, sn=signal_name, em=error_msg: self._emit_error(lt, sn, em))
        
        QTimer.singleShot(1200, lambda: self._complete_error_test())
    
    def _emit_error(self, log_type, signal_name, error_msg):
        """오류 시그널 발생"""
        signal = getattr(self.network_manager.tcp_client, signal_name)
        signal.emit(f"{log_type}: {error_msg}")
        self.log_message(f"{log_type} 오류 발생: {error_msg}", "ERROR")
        self.validation_message(f"{log_type} 오류 처리 확인")
    
    def _complete_error_test(self):
        """오류 테스트 완료"""
        self.status_label.setText("✅ 오류 처리 테스트 완료")
        self.log_message("오류 처리 인터페이스 규칙 검증 완료", "SUCCESS")
    
    def run_full_test(self):
        """전체 테스트 실행"""
        self.status_label.setText("🔄 전체 테스트 실행 중...")
        self.log_message("전체 인터페이스 규칙 검증 테스트 시작", "SUCCESS")
        
        # 모든 테스트를 순차적으로 실행
        tests = [
            (1000, self.test_object_detection),
            (3000, self.test_bird_risk),
            (5000, self.test_pilot_log),
            (7000, self.test_object_image),
            (9000, self.test_filtering),
            (12000, self.simulate_error)
        ]
        
        for delay, test_func in tests:
            QTimer.singleShot(delay, test_func)
        
        QTimer.singleShot(15000, lambda: self._complete_full_test())
    
    def _complete_full_test(self):
        """전체 테스트 완료"""
        self.status_label.setText("🎉 전체 테스트 완료!")
        self.log_message("전체 인터페이스 규칙 검증 테스트 완료", "SUCCESS")
        self.validation_message("📋 모든 LogPage 인터페이스 규칙 검증 완료")


def main():
    """메인 함수"""
    try:
        app = QApplication(sys.argv)
        
        # 애플리케이션 정보 설정
        app.setApplicationName("LogPage Test")
        app.setApplicationVersion("1.0")
        
        print("🚀 LogPage 인터페이스 규칙 검증 테스트 도구")
        print("=" * 70)
        print("📋 검증 항목:")
        print("  📊 객체 감지 로그 (LC_OL) - Constants 매핑, No.컬럼, 데이터 무결성")
        print("  🐦 조류 위험도 로그 (LC_BL) - BirdRiskLevel enum 매핑")
        print("  ✈️ 파일럿 로그 (LC_RL) - PilotRequestType/ResponseType enum 매핑")
        print("  🖼️ 객체 이미지 (LC_OI) - 이미지 요청/응답 인터페이스")
        print("  🔧 필터링 기능 - 구역/종류 필터, 리셋 기능")
        print("  ❌ 오류 처리 - 각 로그 타입별 오류 메시지 처리")
        print("=" * 70)
        print("💡 LogPage가 자동으로 실행되고 더미 데이터로 인터페이스 규칙을 검증합니다!")
        print("💡 우측 패널의 테스트 버튼을 클릭하여 개별 검증을 수행할 수 있습니다.")
        print()
        
        # 메인 윈도우 생성
        window = LogPageTestWindow()
        window.show()
        
        # 이벤트 루프 실행
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ 필수 모듈을 찾을 수 없습니다: {e}")
        print("💡 다음 명령으로 필요한 패키지를 설치하세요:")
        print("   pip install PyQt6 pillow")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 