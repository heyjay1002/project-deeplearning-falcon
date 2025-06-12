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
                self.sock.settimeout(5) # 연결 시도 타임아웃
                self.sock.connect((self.host, self.port))
                self.sock.settimeout(None) # 연결 후 블로킹 모드로 복귀
                print(f"[TCP] Connected to server.")
                
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
        while not self.stop_event.is_set():
            try:
                message = self.send_queue.get(timeout=1)
                message_bytes = json.dumps(message).encode('utf-8')
                self.sock.sendall(message_bytes)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TCP] Error sending, closing connection: {e}")
                break

    def _recv_loop(self):
        while not self.stop_event.is_set():
            try:
                data = self.sock.recv(1024)
                if not data:
                    print("[TCP] Server closed connection.")
                    break
                command = json.loads(data.decode('utf-8'))
                self._handle_command(command)
            except Exception as e:
                print(f"[TCP] Error receiving, closing connection: {e}")
                break

    def _handle_command(self, command):
        if command.get("type") == "command":
            cmd_type = command.get("command")
            if cmd_type == "set_object_detect_mode": 
                settings.DETECTOR_CURRENT_MODE = "object_detect"
                response = { "type": "response", "command": cmd_type, "result": "ok" }
                self.send_queue.put(response)

    def stop(self):
        self.stop_event.set()