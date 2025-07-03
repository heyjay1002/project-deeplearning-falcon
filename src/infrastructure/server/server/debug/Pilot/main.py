"""
조종사 GUI 테스트 프로그램
메인 서버와 TCP 통신으로 활주로 상태 및 조류 위험도 정보 요청/수신
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
import json
import random
from network.tcp import TCPClient
from config import *

class PilotClient:
    def __init__(self):
        self.running = True
        
        # TCP 클라이언트 초기화
        self.pilot_client = TCPClient(host=DEFAULT_HOST, port=TCP_PORT_PILOT)
        
        # 요청 명령 목록
        self.commands = ['BR_INQ', 'RWY_A_STATUS', 'RWY_B_STATUS', 'RWY_AVAIL_INQ']
        
        print("[INFO] 조종사 GUI 클라이언트 초기화 완료")
    
    def start(self):
        """클라이언트 시작"""
        if not self.running:
            return False
        
        # 서버 연결
        if not self.pilot_client.start():
            print("[ERROR] 서버 연결 실패")
            return False
        
        print("[INFO] 조종사 GUI 서버 연결 성공")
        
        try:
            # 명령 전송 시작
            self.send_commands()
            return True
            
        except Exception as e:
            print(f"[ERROR] 통신 시작 실패: {e}")
            return False
    
    def send_commands(self):
        """명령 전송"""
        print("[INFO] 조종사 GUI 명령 전송 시작...")
        
        while self.running:
            try:
                # 랜덤하게 명령 선택
                command = random.choice(self.commands)
                
                # 명령 전송
                request = {
                    "type": "command",
                    "command": command
                }
                
                print(f"[INFO] 명령 전송: {command}")
                if self.pilot_client.send_message_json(request):
                    print(f"[INFO] {command} 명령 전송 성공")
                else:
                    print(f"[WARNING] {command} 명령 전송 실패")
                
                # 5-20초 대기  
                time.sleep(random.uniform(5, 20))
                
            except KeyboardInterrupt:
                print("\n[INFO] 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"[ERROR] 명령 전송 중 오류: {e}")
                time.sleep(5)
    
    def stop(self):
        """클라이언트 종료"""
        print("[INFO] 조종사 GUI 클라이언트 종료 중...")
        self.running = False
        
        # 리소스 정리
        self.pilot_client.close()
        
        print("[INFO] 조종사 GUI 클라이언트 종료 완료")

def main():
    """메인 함수"""
    client = PilotClient()
    if client.start():
        try:
            # 프로그램이 계속 실행되도록 대기
            while client.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] 프로그램 종료 중...")
        finally:
            client.stop()
    else:
        print("[ERROR] 조종사 GUI 클라이언트 시작 실패")

if __name__ == '__main__':
    main() 