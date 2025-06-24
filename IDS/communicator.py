# communicator.py
import socket
import threading
import json
import time

class TcpCommunicator(threading.Thread):
    def __init__(self, tcp_queue, mode_queue, settings):
        super().__init__(daemon=True)
        self.tcp_queue = tcp_queue
        self.mode_queue = mode_queue
        self.settings = settings
        self.running = True
        self.sock = None
        self.recv_buffer = ""

    def connect_to_server(self):
        """서버에 연결을 시도하는 함수"""
        if self.sock:
            self.sock.close()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.settings.TCP_COMM_TIMEOUT_MS / 1000.0)
        
        try:
            server_addr = (self.settings.MAIN_SERVER_IP, self.settings.IDS_TCP_PORT)
            self.sock.connect(server_addr)
            # [로그 강화] 연결 성공 로그
            print(f"✅ [연결 성공] TCP 서버({server_addr[0]}:{server_addr[1]})와 연결되었습니다.")
            return True
        except Exception as e:
            # [로그 강화] 연결 실패 로그
            print(f"❌ [연결 실패] TCP 서버 연결에 실패했습니다. 원인: {e}")
            self.sock = None
            return False

    def run(self):
        # [로그 추가] 스레드 시작 시 초기 연결 시도
        print("ℹ️ [연결 시작] TCP 통신 스레드를 시작하고 서버와 연결을 시도합니다.")
        if not self.connect_to_server():
            print("🛑 [스레드 종료] 초기 TCP 연결에 실패하여 스레드를 종료합니다. 5초 후 재시도 로직을 원하시면 수정이 필요합니다.")
            return

        while self.running:
            try:
                # 전송 로직
                if not self.tcp_queue.empty():
                    msg = self.tcp_queue.get_nowait()
                    if isinstance(msg, dict):
                        data_to_send = json.dumps(msg, ensure_ascii=False) + "\n"
                        self.sock.sendall(data_to_send.encode("utf-8"))
                        if self.settings.DISPLAY_DEBUG:
                            print(f"📤 전송됨 (TCP): {data_to_send.strip()}")

                # 수신 로직
                self.sock.settimeout(0.01)
                try:
                    recv_data = self.sock.recv(4096).decode("utf-8")
                    if not recv_data:
                        # [로직 변경] 서버가 연결을 정상 종료하면, 예외를 발생시켜 재연결 로직으로 넘김
                        raise ConnectionError("서버가 연결을 종료했습니다.")
                    
                    self.recv_buffer += recv_data
                except socket.timeout:
                    pass

                # 버퍼 처리 로직
                while "\n" in self.recv_buffer:
                    message_str, self.recv_buffer = self.recv_buffer.split("\n", 1)
                    if message_str:
                        self.process_command(message_str)

            except (socket.error, ConnectionError, BrokenPipeError) as e:
                # [로그 강화] 연결 문제 발생 및 재연결 시도 로그
                print(f"⛔️ [연결 끊김] TCP 연결에 문제가 발생했습니다. 원인: {e}")
                self.sock.close()
                print("⏳ [재연결 시도] 5초 후 서버와 재연결을 시작합니다...")
                time.sleep(5)
                
                if not self.connect_to_server():
                    # [로그 추가] 재연결 실패 시 로그
                    print("❌ [재연결 실패] 재연결에 실패했습니다. 5초 후 다시 시도합니다.")
                    time.sleep(5)
            
            except Exception as e:
                print(f"🔥 [기타 오류] 처리되지 않은 TCP 오류: {e}")
                time.sleep(1)

    def process_command(self, msg_str):
        """수신된 명령을 파싱하고 큐에 넣는 함수"""
        try:
            message = json.loads(msg_str)
            if self.settings.DISPLAY_DEBUG:
                print(f"📥 [TCP 수신] {msg_str}")

            if message.get("type") == "command" and "command" in message:
                command = message["command"]
                self.mode_queue.put(command) 
                print(f"✅ 수신된 명령 실행: {command}")

        except json.JSONDecodeError:
            print(f"⚠️ 잘못된 JSON 형식 수신: {msg_str}")
        except Exception as e:
            print(f"⚠️ 명령 처리 중 오류 발생: {e}")

    def close(self):
        self.running = False
        if self.sock:
            self.sock.close()
        print("🛑 [스레드 종료] TCP 통신 스레드가 종료되었습니다.")