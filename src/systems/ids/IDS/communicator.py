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
            print(f"✅ [연결 성공] TCP 서버({server_addr[0]}:{server_addr[1]})와 연결되었습니다.")
            return True
        except Exception as e:
            # 연결 실패는 재시도 로직에서 관리하므로, 여기서는 로그만 남기고 실패를 반환
            # print(f"❌ [연결 실패] TCP 서버 연결에 실패했습니다. 원인: {e}")
            self.sock = None
            return False

    def run(self):
        """
        [로직 개선] 메인 스레드 루프.
        - 초기 연결 실패 시 스레드가 종료되지 않고, 메인 루프 안에서 계속 재연결을 시도합니다.
        - 연결이 끊겼을 때도 동일한 로직으로 안정적으로 재연결을 수행합니다.
        """
        print("ℹ️ [스레드 시작] TCP 통신 스레드를 시작합니다.")

        while self.running:
            try:
                # [핵심 수정] 소켓이 연결되지 않은 상태라면 먼저 연결 시도
                if self.sock is None:
                    if not self.connect_to_server():
                        print("⏳ [재연결 대기] 서버 연결에 실패했습니다. 5초 후 재시도합니다.")
                        time.sleep(5)
                        continue  # 루프의 처음으로 돌아가 재시도

                # --- 이하 로직은 소켓이 정상 연결된 경우에만 수행 ---

                # 1. 전송 로직: tcp_queue에 메시지가 있으면 서버로 전송
                if not self.tcp_queue.empty():
                    msg = self.tcp_queue.get_nowait()
                    if isinstance(msg, dict):
                        data_to_send = json.dumps(msg, ensure_ascii=False) + "\n"
                        self.sock.sendall(data_to_send.encode("utf-8"))
                        if self.settings.DISPLAY_DEBUG:
                            print(f"📤 전송됨 (TCP): {data_to_send.strip()}")

                # 2. 수신 로직: non-blocking으로 서버로부터 데이터 수신
                self.sock.settimeout(0.01) # 짧은 타임아웃으로 non-blocking 효과
                try:
                    recv_data = self.sock.recv(4096).decode("utf-8")
                    if not recv_data:
                        # 서버가 연결을 정상 종료한 경우
                        raise ConnectionError("서버가 연결을 종료했습니다.")
                    
                    self.recv_buffer += recv_data
                except socket.timeout:
                    # 데이터가 없는 것은 정상적인 상황이므로 통과
                    pass

                # 3. 버퍼 처리 로직: 수신된 데이터가 완전한 메시지(\n 기준)를 이루면 처리
                while "\n" in self.recv_buffer:
                    message_str, self.recv_buffer = self.recv_buffer.split("\n", 1)
                    if message_str:
                        self.process_command(message_str)

            except (socket.error, ConnectionError, BrokenPipeError) as e:
                # [핵심 수정] 예외 발생 시 재연결을 위해 소켓을 None으로 설정
                print(f"⛔️ [연결 끊김] TCP 연결에 문제가 발생했습니다. 원인: {e}")
                if self.sock:
                    self.sock.close()
                self.sock = None # 다음 루프에서 재연결을 시도하도록 상태 변경
                
                print("⏳ [재연결 시도] 5초 후 서버와 재연결을 시작합니다...")
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
        """스레드를 안전하게 종료하는 함수"""
        self.running = False
        if self.sock:
            self.sock.close()
        print("🛑 [스레드 종료] TCP 통신 스레드가 종료되었습니다.")