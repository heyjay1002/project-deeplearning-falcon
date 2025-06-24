"""
GUI 자동 실행 CCTV 테스트 서버
- 서버와 GUI를 동시에 실행
- TCP로 CCTV 요청 수신 및 OK 응답  
- UDP로 웹캠 영상 송출
"""

import socket
import threading
import time
import cv2
import subprocess
import sys
import os
from datetime import datetime
from views.main_page import MainPage

class TestServer:
    def __init__(self):
        # 설정 (settings.py 참고)
        self.tcp_port = 5100
        self.udp_port = 4100
        self.running = False
        self.streaming_camera = None
        self.client_address = None
        self.camera = None
        self.image_id = 0
        self.gui_process = None

    def start(self):
        """서버 시작"""
        print("테스트 서버 시작...")
        self.running = True
        
        # 웹캠 초기화
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            print("웹캠을 찾을 수 없습니다")
            return False
        
        # 웹캠 설정
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("웹캠 초기화 완료")
        
        # TCP 서버
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('127.0.0.1', self.tcp_port))
        self.tcp_socket.listen(1)
        
        # UDP 소켓
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 스레드 시작
        threading.Thread(target=self.tcp_loop, daemon=True).start()
        threading.Thread(target=self.udp_loop, daemon=True).start()
        
        print(f"서버 시작됨 - TCP: {self.tcp_port}, UDP: {self.udp_port}")
        
        # GUI 자동 실행
        self.start_gui()
        
        return True

    def start_gui(self):
        """GUI 자동 실행"""
        try:
            # main.py 파일 경로 확인
            script_dir = os.path.dirname(os.path.abspath(__file__))
            main_py_path = os.path.join(script_dir, '../main.py')
            
            if os.path.exists(main_py_path):
                print("GUI 자동 실행 중...")
                # GUI를 별도 프로세스로 실행
                self.gui_process = subprocess.Popen([
                    sys.executable, main_py_path
                ], cwd=script_dir)
                print("GUI 실행됨")
            else:
                print(f"main.py 파일을 찾을 수 없습니다: {main_py_path}")
                print("수동으로 GUI를 실행하세요: python main.py")
                
        except Exception as e:
            print(f"GUI 자동 실행 실패: {e}")
            print("수동으로 GUI를 실행하세요: python main.py")

    def tcp_loop(self):
        """TCP 서버 루프"""
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                self.client_address = addr
                print(f"클라이언트 연결: {addr}")
                
                while self.running:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    message = data.decode('utf-8').strip()
                    print(f"수신: {message}")
                    
                    # constants.py의 MessagePrefix 참고한 응답 처리
                    response = None
                    if message == "MC_CA":  # CCTV A 요청
                        self.streaming_camera = "A"
                        response = "MR_CA:OK"
                        print(f"CCTV A 스트리밍 시작 → UDP 전송 대상: {addr[0]}:4100")
                    elif message == "MC_CB":  # CCTV B 요청
                        self.streaming_camera = "B"
                        response = "MR_CB:OK"
                        print(f"CCTV B 스트리밍 시작 → UDP 전송 대상: {addr[0]}:4100")
                    elif message == "MC_MP":  # 지도 요청
                        response = "MR_MP:OK"
                    elif message == "PING":  # 하트비트
                        response = "PONG"
                    
                    if response:
                        client_socket.send((response + '\n').encode('utf-8'))
                        print(f"응답: {response}")
                    
            except Exception as e:
                if self.running:
                    print(f"TCP 오류: {e}")

    def udp_loop(self):
        """UDP 영상 송출 루프"""
        frame_count = 0
        while self.running:
            if self.streaming_camera and self.client_address and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    self.send_frame(frame)
                    frame_count += 1
                    # 10프레임마다 로그 출력 (더 자주)
                    if frame_count % 10 == 0:
                        print(f"UDP 전송: 카메라 {self.streaming_camera} → {self.client_address[0]}:{self.udp_port} (프레임 {frame_count})")
                time.sleep(1/15)  # 15fps
            else:
                if self.streaming_camera and not self.client_address:
                    print("클라이언트 주소가 없습니다. TCP 연결을 먼저 해주세요.")
                time.sleep(0.1)

    def send_frame(self, frame):
        """UDP로 프레임 전송"""
        try:
            # 카메라 정보 오버레이
            cv2.putText(frame, f"Camera {self.streaming_camera}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Frame: {self.image_id}", 
                       (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # JPEG 인코딩 (constants.py Video 클래스 참고)
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 80]
            _, encoded = cv2.imencode('.jpg', frame, encode_param)
            
            # udp_client.py _parse_frame_header 메서드 형식에 맞춘 헤더
            header = f"{self.streaming_camera}:{self.image_id}:".encode('utf-8')
            data = header + encoded.tobytes()
            
            # 전송 (IP와 포트 정보 출력)
            target_addr = (self.client_address[0], self.udp_port)
            self.udp_socket.sendto(data, target_addr)
            
            # 첫 번째와 매 50번째 프레임에서 상세 정보 출력
            if self.image_id == 1 or self.image_id % 50 == 0:
                print(f"프레임 전송 상세: {len(data)} bytes → {target_addr}")
                print(f"  헤더: {header}")
                print(f"  이미지 크기: {len(encoded)} bytes")
            
            self.image_id += 1
            
        except Exception as e:
            print(f"프레임 전송 오류: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """서버 중지"""
        print("서버 종료 중...")
        self.running = False
        
        # 웹캠 해제
        if self.camera:
            self.camera.release()
            
        # 소켓 닫기
        if hasattr(self, 'tcp_socket'):
            self.tcp_socket.close()
        if hasattr(self, 'udp_socket'):
            self.udp_socket.close()
            
        # GUI 프로세스 종료
        if self.gui_process and self.gui_process.poll() is None:
            print("GUI 프로세스 종료 중...")
            self.gui_process.terminate()
            try:
                self.gui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.gui_process.kill()
                
        print("서버 중지 완료")

def main():
    print("=== CCTV 테스트 환경 ===")
    print("웹캠과 GUI를 자동으로 시작합니다.")
    print("Ctrl+C로 종료하세요.")
    print()
    
    server = TestServer()
    if server.start():
        try:
            print("서버가 실행 중입니다...")
            print("GUI가 자동으로 실행됩니다.")
            print("GUI에서 'CCTV 보기' 버튼을 클릭하여 테스트하세요.")
            print()
            
            while True:
                time.sleep(1)
                # GUI 프로세스가 종료되었는지 확인
                if server.gui_process and server.gui_process.poll() is not None:
                    print("GUI가 종료되었습니다. 서버도 종료합니다.")
                    break
                    
        except KeyboardInterrupt:
            print("\nCtrl+C로 종료...")
        finally:
            server.stop()
    else:
        print("서버 시작 실패")

if __name__ == "__main__":
    main()