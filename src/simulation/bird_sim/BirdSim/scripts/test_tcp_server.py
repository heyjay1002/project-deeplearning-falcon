#!/usr/bin/env python3
"""
간단한 TCP 테스트 서버 (포트 5200)
BDS 실시간 파이프라인의 TCP 연결 테스트용
"""

import socket
import threading
import json
import time
from datetime import datetime

class TestTCPServer:
    def __init__(self, host='localhost', port=5200):
        self.host = host
        self.port = port
        self.running = False
        self.clients = []
        
    def start(self):
        """서버 시작"""
        self.running = True
        
        # 소켓 생성
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"🚀 테스트 TCP 서버 시작: {self.host}:{self.port}")
            print("📡 BDS 클라이언트 연결 대기 중...")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"✅ 클라이언트 연결됨: {address}")
                    
                    # 클라이언트 처리 스레드 시작
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"❌ 연결 수락 오류: {e}")
                        
        except Exception as e:
            print(f"❌ 서버 시작 실패: {e}")
        finally:
            self.server_socket.close()
    
    def handle_client(self, client_socket, address):
        """클라이언트 메시지 처리 (BDS 형식: JSON + 줄바꿈)"""
        try:
            # 수신 버퍼
            buffer = b''
            
            while self.running:
                # 데이터 수신
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                
                buffer += chunk
                
                # 줄바꿈으로 메시지 분리
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    
                    if line.strip():  # 빈 줄이 아니면
                        try:
                            message_str = line.decode('utf-8')
                            print(f"📨 원본 메시지 수신: {message_str}")
                            message = json.loads(message_str)
                            self.process_message(message, address)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON 디코딩 오류: {e}")
                            print(f"   원본 데이터: {line[:100]}...")  # 처음 100바이트만 출력
                
        except Exception as e:
            print(f"❌ 클라이언트 처리 오류 ({address}): {e}")
        finally:
            client_socket.close()
            print(f"🔌 클라이언트 연결 종료: {address}")
    
    def process_message(self, message, address):
        """메시지 처리 및 출력"""
        msg_type = message.get('type', 'unknown')
        timestamp = datetime.fromtimestamp(message.get('timestamp', time.time()))
        
        if msg_type == 'event':
            # BDS 실제 메시지 형식에 맞춰 처리
            event_type = message.get('event', 'UNKNOWN')
            
            if event_type == 'BR_CHANGED':
                # BDS에서 전송하는 위험도 레벨 (BR_HIGH, BR_MEDIUM, BR_LOW)
                br_level = message.get('result', 'UNKNOWN')
                
                # BR_ 레벨을 로그 표시로 매핑
                level_mapping = {
                    'BR_HIGH': ('🔴', 'WARNING'),
                    'BR_MEDIUM': ('🟡', 'CAUTION'), 
                    'BR_LOW': ('🟢', 'CLEAR')
                }
                
                emoji, display_level = level_mapping.get(br_level, ('⚪', 'UNKNOWN'))
                
                print(f"{emoji} 위험도 [{timestamp.strftime('%H:%M:%S')}]: {display_level} from {address[0]}")
            else:
                # 다른 이벤트 타입
                print(f"📨 이벤트 [{timestamp.strftime('%H:%M:%S')}]: {event_type} from {address[0]}")
            
        elif msg_type == 'heartbeat':
            status = message.get('status', 'unknown')
            print(f"💓 하트비트 [{timestamp.strftime('%H:%M:%S')}]: {status} from {address[0]}")
            
        elif msg_type == 'connection':
            status = message.get('status', 'unknown')
            print(f"🔌 연결 상태 [{timestamp.strftime('%H:%M:%S')}]: {status} from {address[0]}")
            
        else:
            print(f"📨 메시지 수신 [{timestamp.strftime('%H:%M:%S')}]: {message}")
    
    def stop(self):
        """서버 중지"""
        print("\n🛑 테스트 서버 중지 중...")
        self.running = False
        if hasattr(self, 'server_socket'):
            self.server_socket.close()

def main():
    """메인 실행"""
    server = TestTCPServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 사용자 중단 요청")
    finally:
        server.stop()
        print("✅ 테스트 서버 종료 완료")

if __name__ == "__main__":
    main() 