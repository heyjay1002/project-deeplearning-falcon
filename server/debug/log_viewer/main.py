#!/usr/bin/env python3
"""
이력 조회 디버그 GUI
- LC_OL: 위험 요소 감지 이력 조회
- LC_OI: 이미지 요청
- LC_BL: 조류 위험도 등급 변화 이력 조회
- LC_RL: 조종사 요청 응답 이력 조회
"""

import sys
import socket
import threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTextEdit, QLineEdit, QLabel, 
                             QDateEdit, QTabWidget, QTableWidget, QTableWidgetItem,
                             QMessageBox, QSplitter, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QPixmap

class TCPClient(QObject):
    """TCP 통신 클라이언트"""
    message_received = pyqtSignal(str)
    binary_received = pyqtSignal(bytes)
    connection_status = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.connected = False
        
    def connect_to_server(self, host='localhost', port=5100):
        """서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.connection_status.emit(True)
            print(f"[INFO] 서버 연결 성공: {host}:{port}")
            
            # 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            print(f"[ERROR] 서버 연결 실패: {e}")
            self.connection_status.emit(False)
            
    def send_command(self, command):
        """명령 전송"""
        if not self.connected or not self.socket:
            print("[ERROR] 서버에 연결되지 않음")
            return False
            
        try:
            self.socket.send(command.encode() + b'\n')
            print(f"[SEND] {command}")
            return True
        except Exception as e:
            print(f"[ERROR] 명령 전송 실패: {e}")
            return False
            
    def _receive_messages(self):
        """메시지 수신 (별도 스레드)"""
        buffer = b''
        
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                    
                buffer += data
                
                # 텍스트 메시지인지 바이너리인지 판단
                if buffer.startswith(b'LR_OI:OK'):
                    # 이미지 응답 처리
                    self.binary_received.emit(buffer)
                    buffer = b''
                elif b'\n' in buffer:
                    # 텍스트 메시지 처리
                    lines = buffer.split(b'\n')
                    for line in lines[:-1]:
                        if line:
                            self.message_received.emit(line.decode())
                    buffer = lines[-1]
                    
            except Exception as e:
                print(f"[ERROR] 메시지 수신 실패: {e}")
                break
                
        self.connected = False
        self.connection_status.emit(False)
        
    def disconnect(self):
        """연결 종료"""
        self.connected = False
        if self.socket:
            self.socket.close()

class LogViewerGUI(QMainWindow):
    """이력 조회 디버그 GUI"""
    
    def __init__(self):
        super().__init__()
        self.tcp_client = TCPClient()
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """UI 초기화"""
        self.setWindowTitle("이력 조회 디버그 GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 연결 상태 패널
        self.setup_connection_panel(main_layout)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 각 탭 생성
        self.setup_detect_events_tab()
        self.setup_bird_risk_tab()
        self.setup_interaction_log_tab()
        self.setup_image_viewer_tab()
        
        # 로그 패널
        self.setup_log_panel(main_layout)
        
    def setup_connection_panel(self, main_layout):
        """연결 패널 설정"""
        conn_group = QGroupBox("서버 연결")
        conn_layout = QHBoxLayout(conn_group)
        
        # 서버 주소
        conn_layout.addWidget(QLabel("서버:"))
        self.host_edit = QLineEdit("localhost")
        self.host_edit.setMaximumWidth(100)
        conn_layout.addWidget(self.host_edit)
        
        conn_layout.addWidget(QLabel("포트:"))
        self.port_edit = QLineEdit("5100")
        self.port_edit.setMaximumWidth(80)
        conn_layout.addWidget(self.port_edit)
        
        # 연결 버튼
        self.connect_btn = QPushButton("연결")
        self.connect_btn.clicked.connect(self.connect_to_server)
        conn_layout.addWidget(self.connect_btn)
        
        # 상태 표시
        self.status_label = QLabel("연결 안됨")
        self.status_label.setStyleSheet("color: red;")
        conn_layout.addWidget(self.status_label)
        
        conn_layout.addStretch()
        main_layout.addWidget(conn_group)
        
    def setup_detect_events_tab(self):
        """감지 이벤트 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 날짜 선택
        date_group = QGroupBox("조회 조건")
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("시작 날짜:"))
        self.de_start_date = QDateEdit()
        self.de_start_date.setDate(QDate.currentDate())
        self.de_start_date.setCalendarPopup(True)
        date_layout.addWidget(self.de_start_date)
        
        date_layout.addWidget(QLabel("끝 날짜:"))
        self.de_end_date = QDateEdit()
        self.de_end_date.setDate(QDate.currentDate())
        self.de_end_date.setCalendarPopup(True)
        date_layout.addWidget(self.de_end_date)
        
        self.de_query_btn = QPushButton("조회 (LC_OL)")
        self.de_query_btn.clicked.connect(self.query_detect_events)
        date_layout.addWidget(self.de_query_btn)
        
        date_layout.addStretch()
        layout.addWidget(date_group)
        
        # 결과 테이블
        self.de_table = QTableWidget()
        self.de_table.setColumnCount(5)
        self.de_table.setHorizontalHeaderLabels(["Event Type", "Object ID", "Object Type", "Area", "Timestamp"])
        self.de_table.cellDoubleClicked.connect(self.on_detect_event_double_click)
        layout.addWidget(self.de_table)
        
        self.tab_widget.addTab(tab, "감지 이벤트 (LC_OL)")
        
    def setup_bird_risk_tab(self):
        """조류 위험도 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 날짜 선택
        date_group = QGroupBox("조회 조건")
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("시작 날짜:"))
        self.br_start_date = QDateEdit()
        self.br_start_date.setDate(QDate.currentDate())
        self.br_start_date.setCalendarPopup(True)
        date_layout.addWidget(self.br_start_date)
        
        date_layout.addWidget(QLabel("끝 날짜:"))
        self.br_end_date = QDateEdit()
        self.br_end_date.setDate(QDate.currentDate())
        self.br_end_date.setCalendarPopup(True)
        date_layout.addWidget(self.br_end_date)
        
        self.br_query_btn = QPushButton("조회 (LC_BL)")
        self.br_query_btn.clicked.connect(self.query_bird_risk)
        date_layout.addWidget(self.br_query_btn)
        
        date_layout.addStretch()
        layout.addWidget(date_group)
        
        # 결과 테이블
        self.br_table = QTableWidget()
        self.br_table.setColumnCount(2)
        self.br_table.setHorizontalHeaderLabels(["Risk Level", "Timestamp"])
        layout.addWidget(self.br_table)
        
        self.tab_widget.addTab(tab, "조류 위험도 (LC_BL)")
        
    def setup_interaction_log_tab(self):
        """상호작용 로그 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 날짜 선택
        date_group = QGroupBox("조회 조건")
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("시작 날짜:"))
        self.il_start_date = QDateEdit()
        self.il_start_date.setDate(QDate.currentDate())
        self.il_start_date.setCalendarPopup(True)
        date_layout.addWidget(self.il_start_date)
        
        date_layout.addWidget(QLabel("끝 날짜:"))
        self.il_end_date = QDateEdit()
        self.il_end_date.setDate(QDate.currentDate())
        self.il_end_date.setCalendarPopup(True)
        date_layout.addWidget(self.il_end_date)
        
        self.il_query_btn = QPushButton("조회 (LC_RL)")
        self.il_query_btn.clicked.connect(self.query_interaction_log)
        date_layout.addWidget(self.il_query_btn)
        
        date_layout.addStretch()
        layout.addWidget(date_group)
        
        # 결과 테이블
        self.il_table = QTableWidget()
        self.il_table.setColumnCount(4)
        self.il_table.setHorizontalHeaderLabels(["Request Type", "Response Type", "Request Time", "Response Time"])
        layout.addWidget(self.il_table)
        
        self.tab_widget.addTab(tab, "상호작용 로그 (LC_RL)")
        
    def setup_image_viewer_tab(self):
        """이미지 뷰어 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 이미지 요청
        img_group = QGroupBox("이미지 요청")
        img_layout = QHBoxLayout(img_group)
        
        img_layout.addWidget(QLabel("Object ID:"))
        self.object_id_edit = QLineEdit()
        self.object_id_edit.setPlaceholderText("예: 1750995441567")
        img_layout.addWidget(self.object_id_edit)
        
        self.img_query_btn = QPushButton("이미지 요청 (LC_OI)")
        self.img_query_btn.clicked.connect(self.query_image)
        img_layout.addWidget(self.img_query_btn)
        
        img_layout.addStretch()
        layout.addWidget(img_group)
        
        # 이미지 표시
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setText("이미지가 표시됩니다")
        layout.addWidget(self.image_label)
        
        self.tab_widget.addTab(tab, "이미지 뷰어 (LC_OI)")
        
    def setup_log_panel(self, main_layout):
        """로그 패널 설정"""
        log_group = QGroupBox("통신 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # 로그 제어 버튼
        log_btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("로그 지우기")
        clear_btn.clicked.connect(self.log_text.clear)
        log_btn_layout.addWidget(clear_btn)
        
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        
        main_layout.addWidget(log_group)
        
    def setup_connections(self):
        """시그널 연결"""
        self.tcp_client.message_received.connect(self.on_message_received)
        self.tcp_client.binary_received.connect(self.on_binary_received)
        self.tcp_client.connection_status.connect(self.on_connection_status)
        
    def connect_to_server(self):
        """서버 연결"""
        host = self.host_edit.text()
        port = int(self.port_edit.text())
        
        self.tcp_client.connect_to_server(host, port)
        
    def on_connection_status(self, connected):
        """연결 상태 변경"""
        if connected:
            self.status_label.setText("연결됨")
            self.status_label.setStyleSheet("color: green;")
            self.connect_btn.setText("연결 해제")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_from_server)
        else:
            self.status_label.setText("연결 안됨")
            self.status_label.setStyleSheet("color: red;")
            self.connect_btn.setText("연결")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.connect_to_server)
            
    def disconnect_from_server(self):
        """서버 연결 해제"""
        self.tcp_client.disconnect()
        
    def query_detect_events(self):
        """감지 이벤트 조회"""
        start_date = self.de_start_date.date().toString("yyyy-MM-dd")
        end_date = self.de_end_date.date().toString("yyyy-MM-dd")
        
        command = f"LC_OL:{start_date},{end_date}"
        self.tcp_client.send_command(command)
        
    def query_bird_risk(self):
        """조류 위험도 조회"""
        start_date = self.br_start_date.date().toString("yyyy-MM-dd")
        end_date = self.br_end_date.date().toString("yyyy-MM-dd")
        
        command = f"LC_BL:{start_date},{end_date}"
        self.tcp_client.send_command(command)
        
    def query_interaction_log(self):
        """상호작용 로그 조회"""
        start_date = self.il_start_date.date().toString("yyyy-MM-dd")
        end_date = self.il_end_date.date().toString("yyyy-MM-dd")
        
        command = f"LC_RL:{start_date},{end_date}"
        self.tcp_client.send_command(command)
        
    def query_image(self):
        """이미지 요청"""
        object_id = self.object_id_edit.text().strip()
        if not object_id:
            QMessageBox.warning(self, "경고", "Object ID를 입력하세요")
            return
            
        command = f"LC_OI:{object_id}"
        self.tcp_client.send_command(command)
        
    def on_detect_event_double_click(self, row, column):
        """감지 이벤트 더블클릭 - 이미지 보기"""
        if column == 1:  # Object ID 컬럼
            object_id = self.de_table.item(row, 1).text()
            self.object_id_edit.setText(object_id)
            self.tab_widget.setCurrentIndex(3)  # 이미지 뷰어 탭으로 이동
            self.query_image()
            
    def on_message_received(self, message):
        """메시지 수신 처리"""
        self.add_log(f"[RECV] {message}")
        
        if message.startswith("LR_OL:"):
            self.handle_detect_events_response(message)
        elif message.startswith("LR_BL:"):
            self.handle_bird_risk_response(message)
        elif message.startswith("LR_RL:"):
            self.handle_interaction_log_response(message)
        elif message.startswith("LR_OI:"):
            self.handle_image_response(message)
            
    def on_binary_received(self, data):
        """바이너리 데이터 수신 처리"""
        self.add_log(f"[RECV] 바이너리 데이터 {len(data)} bytes")
        self.handle_image_binary(data)
        
    def handle_detect_events_response(self, message):
        """감지 이벤트 응답 처리"""
        try:
            if message.startswith("LR_OL:OK,"):
                data = message[9:]  # "LR_OL:OK," 제거
                
                self.de_table.setRowCount(0)
                
                if data.strip():  # 데이터가 있는 경우
                    events = data.split(';')
                    self.de_table.setRowCount(len(events))
                    
                    for i, event in enumerate(events):
                        if event.strip():
                            parts = event.split(',')
                            if len(parts) >= 5:
                                self.de_table.setItem(i, 0, QTableWidgetItem(parts[0]))  # event_type
                                self.de_table.setItem(i, 1, QTableWidgetItem(parts[1]))  # object_id
                                self.de_table.setItem(i, 2, QTableWidgetItem(parts[2]))  # object_type
                                self.de_table.setItem(i, 3, QTableWidgetItem(parts[3]))  # area
                                self.de_table.setItem(i, 4, QTableWidgetItem(parts[4]))  # timestamp
                                
                self.de_table.resizeColumnsToContents()
                
        except Exception as e:
            self.add_log(f"[ERROR] 감지 이벤트 응답 처리 실패: {e}")
            
    def handle_bird_risk_response(self, message):
        """조류 위험도 응답 처리"""
        try:
            if message.startswith("LR_BL:OK,"):
                data = message[9:]  # "LR_BL:OK," 제거
                
                self.br_table.setRowCount(0)
                
                if data.strip():  # 데이터가 있는 경우
                    logs = data.split(';')
                    self.br_table.setRowCount(len(logs))
                    
                    for i, log in enumerate(logs):
                        if log.strip():
                            parts = log.split(',')
                            if len(parts) >= 2:
                                # risk_level_id를 텍스트로 변환
                                risk_level_text = {
                                    '1': 'HIGH',
                                    '2': 'MEDIUM', 
                                    '3': 'LOW'
                                }.get(parts[0], parts[0])
                                self.br_table.setItem(i, 0, QTableWidgetItem(risk_level_text))  # risk_level
                                self.br_table.setItem(i, 1, QTableWidgetItem(parts[1]))  # timestamp
                                
                self.br_table.resizeColumnsToContents()
                
        except Exception as e:
            self.add_log(f"[ERROR] 조류 위험도 응답 처리 실패: {e}")
            
    def handle_interaction_log_response(self, message):
        """상호작용 로그 응답 처리"""
        try:
            if message.startswith("LR_RL:OK,"):
                data = message[9:]  # "LR_RL:OK," 제거
                
                self.il_table.setRowCount(0)
                
                if data.strip():  # 데이터가 있는 경우
                    logs = data.split(';')
                    self.il_table.setRowCount(len(logs))
                    
                    for i, log in enumerate(logs):
                        if log.strip():
                            parts = log.split(',')
                            if len(parts) >= 4:
                                # request_type_id를 텍스트로 변환
                                request_text = {
                                    '1': 'BR_INQ',
                                    '2': 'RWY_A_STATUS',
                                    '3': 'RWY_B_STATUS', 
                                    '4': 'RWY_AVAILABILITY'
                                }.get(parts[0], parts[0])
                                
                                # response_type_id를 텍스트로 변환
                                response_text = {
                                    '1': 'BR_HIGH',
                                    '2': 'BR_MEDIUM',
                                    '3': 'BR_LOW',
                                    '4': 'RWY_OCCUPIED',
                                    '5': 'RWY_CLEAR',
                                    '6': 'RWY_AVAILABLE',
                                    '7': 'RWY_UNAVAILABLE',
                                    '8': 'TAXI_APPROVED',
                                    '9': 'TAXI_DENIED'
                                }.get(parts[1], parts[1])
                                
                                self.il_table.setItem(i, 0, QTableWidgetItem(request_text))  # request_type
                                self.il_table.setItem(i, 1, QTableWidgetItem(response_text))  # response_type
                                self.il_table.setItem(i, 2, QTableWidgetItem(parts[2]))  # request_time
                                self.il_table.setItem(i, 3, QTableWidgetItem(parts[3]))  # response_time
                                
                self.il_table.resizeColumnsToContents()
                
        except Exception as e:
            self.add_log(f"[ERROR] 상호작용 로그 응답 처리 실패: {e}")
            
    def handle_image_response(self, message):
        """이미지 응답 처리 (텍스트 부분)"""
        if message.startswith("LR_OI:ERR"):
            self.add_log(f"[ERROR] 이미지 요청 실패: {message}")
            
    def handle_image_binary(self, data):
        """이미지 바이너리 처리"""
        try:
            # "LR_OI:OK,size," 부분을 찾아서 이미지 데이터 추출
            header_end = data.find(b',', data.find(b',') + 1) + 1  # 두 번째 콤마 다음
            image_data = data[header_end:]
            
            # QPixmap으로 이미지 로드
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # 이미지 크기 조정 (최대 400x400)
                scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.add_log(f"[INFO] 이미지 표시 완료: {len(image_data)} bytes")
            else:
                self.add_log("[ERROR] 이미지 로드 실패")
                
        except Exception as e:
            self.add_log(f"[ERROR] 이미지 처리 실패: {e}")
            
    def add_log(self, message):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 스크롤을 맨 아래로
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def main():
    app = QApplication(sys.argv)
    
    # 윈도우 생성
    window = LogViewerGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()