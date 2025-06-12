# transport/tcp_communicator.py

import socket
import threading
import queue
import json
import time
from config.config import settings

class TcpCommunicator(threading.Thread):
    def __init__(self, send_queue):
        super().__init__()
        self.host = settings.MAIN_SERVER_IP
        self.port = settings.IDS_TCP_PORT
        self.send_queue = send_queue
        self.sock = None
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                print(f"[TCP] Trying to connect to {self.host}:{self.port}")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5)
                self.sock.connect((self.host, self.port))
                self.sock.settimeout(None)
                
                server_address = self.sock.getpeername()
                print(f"[TCP] Successfully connected to server at {server_address[0]}:{server_address[1]}")

                send_thread = threading.Thread(target=self._send_loop, daemon=True)
                recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
                send_thread.start()
                recv_thread.start()

                while send_thread.is_alive() and recv_thread.is_alive() and not self.stop_event.is_set():
                    time.sleep(1)

            except Exception as e:
                print(f"[TCP] Connection failed: {e}. Retrying in 5 seconds...")
            finally:
                if self.sock: self.sock.close()

            if not self.stop_event.is_set():
                time.sleep(5)
        print("[TCP] Communicator stopped.")
        
    def _send_loop(self):
        """큐에 메시지가 있으면 JSON 문자열 끝에 '\n'을 붙여 전송합니다."""
        while not self.stop_event.is_set():
            try:
                message_dict = self.send_queue.get(timeout=1)
                
                # --- 여기가 핵심 수정 부분입니다! ---
                # 1. 메시지를 JSON 문자열로 변환하고, 끝에 줄바꿈(\n)을 추가합니다.
                json_string = json.dumps(message_dict, ensure_ascii=False) + '\n'
                
                # 2. UTF-8 바이트로 인코딩하여 전송합니다.
                message_bytes = json_string.encode('utf-8')
                self.sock.sendall(message_bytes)
                # --- --------------------------- ---

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TCP] Error sending, closing connection: {e}")
                break

    def _recv_loop(self):
        """서버로부터 명령을 수신합니다."""
        buffer = ""
        while not self.stop_event.is_set():
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[TCP] Server closed connection.")
                    break
                
                buffer += data.decode('utf-8')
                
                # 수신 버퍼에서도 '\n'을 기준으로 메시지를 나눔
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str:
                        command = json.loads(message_str)
                        self._handle_command(command)

            except Exception as e:
                print(f"[TCP] Error receiving, closing connection: {e}")
                break

    def _handle_command(self, command):
        """수신한 명령을 처리합니다."""
        if command.get("type") == "command":
            cmd_type = command.get("command")
            if cmd_type == "set_object_detect_mode": 
                settings.DETECTOR_CURRENT_MODE = "object_detect"
                response = { "type": "response", "command": cmd_type, "result": "ok" }
                self.send_queue.put(response)

    def stop(self):
        self.stop_event.set()