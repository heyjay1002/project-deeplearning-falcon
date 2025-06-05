import sys
import os
from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QButtonGroup
import random
import time
from datetime import datetime, timezone

# 음성 처리 스레드
class VoiceProcessingThread(QThread):
    status_changed = pyqtSignal(str)
    stt_result = pyqtSignal(str)
    tts_text = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.callsign = "KAL123"
    
    # 콜사인 설정
    def set_callsign(self, callsign):
        self.callsign = callsign
        
    # 음성 처리 시작
    def start_processing(self):
        self.is_running = True
        self.start()
        
    # 음성 처리 중지
    def stop_processing(self):
        self.is_running = False
        
    # 음성 처리 워크플로우
    def run(self):  
        if not self.is_running:
            return
            
        # 1. 음성 인식 단계
        self.status_changed.emit("LISTENING...")
        self.msleep(2000)  # 2초 대기
        
        if not self.is_running:
            return
            
        # 시뮬레이션된 STT 결과
        stt_samples = [
            f"{self.callsign}, request runway A status check",
            f"{self.callsign}, request bird activity information", 
            f"{self.callsign}, what is the FOD detection status?",
            f"{self.callsign}, request system status check",
            f"{self.callsign}, request emergency procedure guidance",
            f"{self.callsign}, request runway B closure",
            f"{self.callsign}, request bird alert level increase",
            f"{self.callsign}, request landing clearance",
            f"{self.callsign}, ready for takeoff"
        ]
        
        stt_text = random.choice(stt_samples)
        self.stt_result.emit(stt_text)
        
        # 2. 처리 단계
        self.status_changed.emit("PROCESSING...")
        self.msleep(1500)  # 1.5초 대기
        
        if not self.is_running:
            return
            
        # 3. TTS 응답 생성
        tts_responses = {
            f"{self.callsign}, request runway A status check": f"{self.callsign}, runway A is currently safe. Risk level LOW, no bird activity, no FOD detected.",
            f"{self.callsign}, request bird activity information": f"{self.callsign}, bird activity detected at medium level. 3-5 small birds observed in perimeter area around runway.",
            f"{self.callsign}, what is the FOD detection status?": f"{self.callsign}, FOD detection system operating normally. No hazardous debris detected so far.",
            f"{self.callsign}, request system status check": f"{self.callsign}, FALCON system status: All sensors operational, communication link good, LLM service active.",
            f"{self.callsign}, request emergency procedure guidance": f"{self.callsign}, emergency procedures: 1) Report to control tower immediately 2) Close affected runway 3) Request safety team dispatch 4) Stand by until situation cleared.",
            f"{self.callsign}, request runway B closure": f"{self.callsign}, runway B closure request received. Notifying control tower and proceeding with immediate closure procedures.",
            f"{self.callsign}, request bird alert level increase": f"{self.callsign}, bird alert level raised to HIGH. Issuing caution alert to all aircraft.",
            f"{self.callsign}, request landing clearance": f"{self.callsign}, cleared to land runway A. Wind 270 degrees at 5 knots, visibility 10km plus. After landing, taxi via taxiway A3.",
            f"{self.callsign}, ready for takeoff": f"{self.callsign}, cleared for takeoff runway B. After takeoff, turn left and climb to 3000 feet."
        }
        
        tts_text = tts_responses.get(stt_text, f"{self.callsign}, request processed. Please advise if you need additional information.")
        self.tts_text.emit(tts_text)
        
        # 4. TTS 재생 단계
        self.status_changed.emit("SPEAKING...")
        self.msleep(3000)  # 3초 대기 (TTS 재생 시뮬레이션)
        
        # 5. 완료
        self.status_changed.emit("READY")
        self.finished.emit()
        self.is_running = False

# 메인 윈도우
class PilotInterfaceAvionics(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # UI 파일 로드
        ui_file = os.path.join(os.path.dirname(__file__), 'pilot_interface.ui')
        uic.loadUi(ui_file, self)
        
        # 초기화
        self.init_ui()
        # self.init_button_groups()
        self.init_timers()
        self.init_voice_thread()
        
    # UI 초기화
    def init_ui(self):
        self.setWindowTitle("FALCON Pilot Interface")
        self.setFixedSize(910, 520)
        
        # 버튼 연결
        self.btn_mic.clicked.connect(self.toggle_voice_processing)
        self.btn_rwy_a.clicked.connect(self.toggle_rwy_a)
        self.btn_rwy_b.clicked.connect(self.toggle_rwy_b)
        self.btn_bird.clicked.connect(self.cycle_bird_alert)
        
        # TTS 볼륨 슬라이더 연결
        self.slider_tts_volume.valueChanged.connect(self.update_tts_volume)
        
        # 초기 상태 설정
        self.rwy_a_state = "CLEARED"  # CLEARED, BLOCKED
        self.rwy_b_state = "CLEARED"  # CLEARED, BLOCKED
        self.bird_state = "CLEAR"     # CLEAR, LOW, MEDIUM, HIGH
        
        # 음성 처리 상태
        self.is_voice_active = False
        
        # 콜사인 목록
        self.callsigns = [
            "KAL123", "AAR456", "UAL789", "DLH012", 
            "SIA345", "JAL678", "ANA901", "CPA234",
            "BAW567", "AFR890", "LHT123", "THA456"
        ]
        self.current_callsign = "KAL123"
        
        # 초기 버튼 상태 설정
        self.update_rwy_a_display()
        self.update_rwy_b_display()
        self.update_bird_display()
    
    # # 버튼 그룹 초기화
    # def init_button_groups(self):
    #     pass
        

    # 타이머 초기화
    def init_timers(self):
        # STT 볼륨 시뮬레이션 타이머
        self.stt_timer = QTimer()
        self.stt_timer.timeout.connect(self.update_stt_volume)
        self.stt_timer.start(100)
        
        # 시간 업데이트 타이머
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_display)
        self.time_timer.start(1000)
        
        # 초기 시간 표시
        self.update_time_display()
        
    # 음성 처리 스레드 초기화
    def init_voice_thread(self):
        self.voice_thread = VoiceProcessingThread()
        self.voice_thread.status_changed.connect(self.update_status)
        self.voice_thread.stt_result.connect(self.display_stt_result)
        self.voice_thread.tts_text.connect(self.display_tts_text)
        self.voice_thread.finished.connect(self.on_voice_finished)
        
    # 음성 처리 토글
    def toggle_voice_processing(self):
        if self.is_voice_active:
            self.stop_voice_processing()
        else:
            self.start_voice_processing()
        
    # 음성 처리 시작
    def start_voice_processing(self):
        self.is_voice_active = True
        self.btn_mic.setText("STOP")
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                border: 4px solid #00ff00;
                border-radius: 6px;
                color: #00ff00;
            }
            QPushButton:hover {
                background-color: #004400;
                border-color: #66ff66;
            }
            QPushButton:pressed {
                background-color: #002200;
            }
        """)
        
        # 텍스트 영역 초기화
        self.text_stt_result.clear()
        self.text_tts_input.clear()
        
        # 새로운 콜사인으로 변경
        self.current_callsign = random.choice(self.callsigns)
        self.label_callsign.setText(f"CALLSIGN: {self.current_callsign}")
        
        # 음성 처리 시작
        self.voice_thread.set_callsign(self.current_callsign)
        self.voice_thread.start_processing()
        
    # 음성 처리 중지
    def stop_voice_processing(self):
        self.voice_thread.stop_processing()
        self.on_voice_finished()
        
    # 음성 처리 완료
    def on_voice_finished(self):
        self.is_voice_active = False
        self.btn_mic.setText("MIC")
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: #001a00;
                border: 4px solid #00ff00;
                border-radius: 6px;
                color: #00ff00;
            }
            QPushButton:hover {
                background-color: #003300;
                border-color: #66ff66;
            }
            QPushButton:pressed {
                background-color: #000d00;
            }
        """)
        
    # 상태 업데이트
    def update_status(self, status):
        self.label_status.setText(status)
        
        # HUD 스타일 색상 - 다양한 색상으로 구분
        status_styles = {
            "READY": {
                "color": "#0099ff",
                "bg_color": "#001133",
                "border_color": "#0099ff"
            },
            "LISTENING...": {
                "color": "#00ff00", 
                "bg_color": "#003300",
                "border_color": "#00ff00"
            },
            "PROCESSING...": {
                "color": "#ff9900",
                "bg_color": "#331a00", 
                "border_color": "#ff9900"
            },
            "SPEAKING...": {
                "color": "#ff3333",
                "bg_color": "#330000",
                "border_color": "#ff3333"
            }
        }
        
        # 상태 스타일 설정
        style_info = status_styles.get(status, status_styles["READY"])
        
        self.label_status.setStyleSheet(f"""
            QLabel {{
                background-color: {style_info['bg_color']};
                border: 2px solid {style_info['border_color']};
                border-radius: 8px;
                padding: 8px;
                color: {style_info['color']};
                font-weight: bold;
                font-family: "Courier New", monospace;
            }}
        """)
        
    # STT 결과 표시
    def display_stt_result(self, text):
        self.text_stt_result.setPlainText(text)
        
    # TTS 텍스트 표시
    def display_tts_text(self, text):
        self.text_tts_input.setPlainText(text)
        
    # TTS 볼륨 업데이트
    def update_tts_volume(self, value):
        self.label_tts_value.setText(str(value))
        
    # STT 볼륨 업데이트
    def update_stt_volume(self):
        # STT 볼륨 시뮬레이션
        if hasattr(self, 'voice_thread') and self.voice_thread.is_running:
            volume = random.randint(40, 90)
        else:
            volume = random.randint(0, 20)
            
        self.progress_stt_volume.setValue(volume)
        
    # 시간 업데이트
    def update_time_display(self):
        # UTC 시간
        utc_time = datetime.now(timezone.utc).strftime('%H:%M:%S')
        self.label_utc_time.setText(f'UTC: {utc_time}')
        
        # 로컬 시간
        local_time = datetime.now().strftime('%H:%M:%S')
        self.label_local_time.setText(f'LOCAL: {local_time}')
        
    # RWY A 상태 변경
    def toggle_rwy_a(self):
        if self.rwy_a_state == "CLEARED":
            self.rwy_a_state = "BLOCKED"
        else:
            self.rwy_a_state = "CLEARED"
        self.update_rwy_a_display()
        
    # RWY B 상태 변경
    def toggle_rwy_b(self):
        if self.rwy_b_state == "CLEARED":
            self.rwy_b_state = "BLOCKED"
        else:
            self.rwy_b_state = "CLEARED"
        self.update_rwy_b_display()
        
    # Bird Alert 상태 변경
    def cycle_bird_alert(self):
        if self.bird_state == "CLEAR":
            self.bird_state = "LOW"
        elif self.bird_state == "LOW":
            self.bird_state = "MEDIUM"
        elif self.bird_state == "MEDIUM":
            self.bird_state = "HIGH"
        else:
            self.bird_state = "CLEAR"
        self.update_bird_display()
        
    # RWY A 상태 표시
    def update_rwy_a_display(self):
        self.btn_rwy_a.setText(self.rwy_a_state)
        
        if self.rwy_a_state == "CLEARED":
            # 녹색
            self.btn_rwy_a.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    border: 2px solid #00ff00;
                    color: #00ff00;
                }
                QPushButton:hover {
                    background-color: #004400;
                    border-color: #33ff33;
                }
                QPushButton:pressed {
                    background-color: #002200;
                }
            """)
        else:  # BLOCKED
            # 빨간색
            self.btn_rwy_a.setStyleSheet("""
                QPushButton {
                    background-color: #330000;
                    border: 2px solid #ff3333;
                    color: #ff3333;
                }
                QPushButton:hover {
                    background-color: #440000;
                    border-color: #ff5555;
                }
                QPushButton:pressed {
                    background-color: #220000;
                }
            """)
        
    # RWY B 상태 표시
    def update_rwy_b_display(self):
        self.btn_rwy_b.setText(self.rwy_b_state)
        
        if self.rwy_b_state == "CLEARED":
            # 녹색
            self.btn_rwy_b.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    border: 2px solid #00ff00;
                    color: #00ff00;
                }
                QPushButton:hover {
                    background-color: #004400;
                    border-color: #33ff33;
                }
                QPushButton:pressed {
                    background-color: #002200;
                }
            """)
        else:  # BLOCKED
            # 빨간색
            self.btn_rwy_b.setStyleSheet("""
                QPushButton {
                    background-color: #330000;
                    border: 2px solid #ff3333;
                    color: #ff3333;
                }
                QPushButton:hover {
                    background-color: #440000;
                    border-color: #ff5555;
                }
                QPushButton:pressed {
                    background-color: #220000;
                }
            """)
        
    # Bird Alert 상태 표시
    def update_bird_display(self):
        self.btn_bird.setText(self.bird_state)
        
        if self.bird_state == "CLEAR" or self.bird_state == "LOW":
            # 녹색
            self.btn_bird.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    border: 2px solid #00ff00;
                    color: #00ff00;
                }
                QPushButton:hover {
                    background-color: #004400;
                    border-color: #33ff33;
                }
                QPushButton:pressed {
                    background-color: #002200;
                }
            """)
        elif self.bird_state == "MEDIUM":
            # 호박색
            self.btn_bird.setStyleSheet("""
                QPushButton {
                    background-color: #331a00;
                    border: 2px solid #ff9900;
                    color: #ff9900;
                }
                QPushButton:hover {
                    background-color: #442200;
                    border-color: #ffaa33;
                }
                QPushButton:pressed {
                    background-color: #221100;
                }
            """)
        else:  # HIGH
            # 빨간색
            self.btn_bird.setStyleSheet("""
                QPushButton {
                    background-color: #330000;
                    border: 2px solid #ff3333;
                    color: #ff3333;
                }
                QPushButton:hover {
                    background-color: #440000;
                    border-color: #ff5555;
                }
                QPushButton:pressed {
                    background-color: #220000;
                }
            """)
        
    def closeEvent(self, event):
        # 윈도우 종료 이벤트
        if hasattr(self, 'voice_thread'):
            self.voice_thread.stop_processing()
            self.voice_thread.quit()
            self.voice_thread.wait()
        event.accept()

def main():
    # 메인 함수
    app = QApplication(sys.argv)
    
    # 항공 전자 스타일 폰트 설정
    font = QtGui.QFont("Courier New", 9)
    app.setFont(font)
    
    # 메인 윈도우 생성 및 표시
    window = PilotInterfaceAvionics()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 