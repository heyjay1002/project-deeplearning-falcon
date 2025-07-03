"""
BDS (Bird Detection System) 테스트 프로그램
메인 서버로 조류 위험도 변경 이벤트를 전송
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
import json
import random
from network.tcp import TCPClient
from config import *

class BDSClient:
    def __init__(self):
        self.running = True
        
        # TCP 클라이언트 초기화
        self.bds_client = TCPClient(host=DEFAULT_HOST, port=TCP_PORT_BIRD)
        
        # 조류 위험도 레벨
        self.risk_levels = ['BR_HIGH', 'BR_MEDIUM', 'BR_LOW']
        self.current_level = 'BR_LOW'
        
        print("[INFO] BDS 클라이언트 초기화 완료")
    
    def start(self):
        """클라이언트 시작"""
        if not self.running:
            return False
        
        # 서버 연결
        if not self.bds_client.start():
            print("[ERROR] 서버 연결 실패")
            return False
        
        print("[INFO] BDS 서버 연결 성공")
        
        try:
            # 조류 위험도 변경 시뮬레이션 시작
            self.simulate_bird_risk_changes()
            return True
            
        except Exception as e:
            print(f"[ERROR] 시뮬레이션 시작 실패: {e}")
            return False
    
    def simulate_bird_risk_changes(self):
        """조류 위험도 변경 시뮬레이션"""
        print("[INFO] 조류 위험도 변경 시뮬레이션 시작...")
        
        while self.running:
            try:
                # 랜덤하게 위험도 변경 (10-30초 간격)
                time.sleep(random.uniform(10, 30))
                
                # 현재 레벨과 다른 레벨로 랜덤 변경
                available_levels = [level for level in self.risk_levels if level != self.current_level]
                new_level = random.choice(available_levels)
                
                # 조류 위험도 변경 메시지 전송
                bds_message = {
                    "type": "event",
                    "event": "BR_CHANGED",
                    "result": new_level
                }
                
                if self.bds_client.send_message_json(bds_message):
                    print(f"[INFO] 조류 위험도 변경 전송 완료: {self.current_level} -> {new_level}")
                    self.current_level = new_level
                else:
                    print(f"[WARNING] 조류 위험도 변경 전송 실패: {new_level}")
                
            except KeyboardInterrupt:
                print("\n[INFO] 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"[ERROR] 시뮬레이션 중 오류: {e}")
                time.sleep(5)  # 오류 발생 시 5초 대기
    
    def stop(self):
        """클라이언트 종료"""
        print("[INFO] BDS 클라이언트 종료 중...")
        self.running = False
        
        # 리소스 정리
        self.bds_client.close()
        
        print("[INFO] BDS 클라이언트 종료 완료")

def main():
    """메인 함수"""
    client = BDSClient()
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
        print("[ERROR] BDS 클라이언트 시작 실패")

if __name__ == '__main__':
    main() 