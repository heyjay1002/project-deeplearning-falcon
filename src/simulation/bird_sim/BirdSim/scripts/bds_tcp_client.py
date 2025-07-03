import socket
import json
import threading
import time
import queue
import logging
from typing import Optional, Dict, Any
from enum import Enum

class RiskLevel(Enum):
    """위험도 레벨 정의 (메인서버 스펙에 맞춤)"""
    BR_HIGH = "BR_HIGH"
    BR_MEDIUM = "BR_MEDIUM"
    BR_LOW = "BR_LOW"
    # BR_NORMAL은 메인서버 스펙에 없으므로 제거됨

class BDSTCPClient:
    """BDS와 Main Server 간의 TCP 통신을 담당하는 클래스"""
    
    def __init__(self, host: str = "localhost", port: int = 5200, 
                 min_send_interval: float = 1.0):
        """
        TCP 클라이언트 초기화
        
        Args:
            host: Main Server 호스트 주소
            port: Main Server 포트 번호 (기본: 5200)
            min_send_interval: 최소 메시지 전송 간격 (초)
        """
        self.host = host
        self.port = port
        self.min_send_interval = min_send_interval
        
        # 연결 관리
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        
        # 메시지 큐 및 상태 관리
        self.message_queue = queue.Queue()
        self.last_sent_risk = None
        self.last_send_time = 0
        
        # 스레드 관리
        self.sender_thread: Optional[threading.Thread] = None
        self.reconnect_thread: Optional[threading.Thread] = None
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
    def start(self) -> bool:
        """TCP 클라이언트 시작"""
        if self.running:
            self.logger.warning("TCP 클라이언트가 이미 실행 중입니다.")
            return True
            
        self.running = True
        
        # 초기 연결 시도
        if not self._connect():
            self.logger.error("초기 연결에 실패했습니다. 재연결을 시도합니다.")
        
        # 메시지 전송 스레드 시작
        self.sender_thread = threading.Thread(target=self._sender_worker, daemon=True)
        self.sender_thread.start()
        
        # 재연결 스레드 시작
        self.reconnect_thread = threading.Thread(target=self._reconnect_worker, daemon=True)
        self.reconnect_thread.start()
        
        self.logger.info(f"BDS TCP 클라이언트가 시작되었습니다. ({self.host}:{self.port})")
        return True
    
    def stop(self):
        """TCP 클라이언트 중지"""
        self.running = False
        self._disconnect()
        
        # 스레드 종료 대기
        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=2.0)
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2.0)
            
        self.logger.info("BDS TCP 클라이언트가 중지되었습니다.")
    
    def send_risk_update(self, risk_level: RiskLevel, additional_data: Optional[Dict[str, Any]] = None):
        """
        위험도 업데이트 메시지 전송 (메인서버 프로토콜 준수)
        
        Args:
            risk_level: 위험도 레벨
            additional_data: 추가 데이터 (선택사항) - 메인서버 스펙에 맞는 경우만 사용
        """
        current_time = time.time()
        
        # 중복 메시지 필터링 (같은 위험도 레벨이고 최소 간격 미달)
        if (self.last_sent_risk == risk_level and 
            current_time - self.last_send_time < self.min_send_interval):
            return
        
        # 위험도 레벨을 Main Server 형식으로 변환
        br_result = self._convert_risk_level(risk_level)
        
        # 메인서버 프로토콜에 정확히 맞는 메시지 형식 (timestamp 제거)
        message = {
            "type": "event",
            "event": "BR_CHANGED", 
            "result": br_result
        }
        
        # 추가 데이터는 메인서버 스펙에 명시된 경우만 포함
        # (현재 스펙에는 없으므로 주석 처리)
        # if additional_data:
        #     message.update(additional_data)
        
        print(f"📡 메인서버 프로토콜 메시지 생성: {message}")
        
        # 메시지 큐에 추가
        try:
            self.message_queue.put_nowait(message)
            self.last_sent_risk = risk_level
            self.last_send_time = current_time
            print(f"✅ 메시지 큐에 추가됨: {br_result}")
        except queue.Full:
            self.logger.warning("메시지 큐가 가득 참. 메시지를 버립니다.")
    
    def send_heartbeat(self):
        """하트비트 메시지 전송 (메인서버 스펙 확인 후 필요시 사용)"""
        # 메인서버 프로토콜에 하트비트가 명시되어 있지 않으므로 전송하지 않음
        # 필요시 메인서버 스펙에 맞춰 활성화
        print("💓 하트비트: 메인서버 스펙에 없음 - 전송 생략")
        return
        
        # 원래 코드 (주석 처리)
        # message = {
        #     "type": "heartbeat",
        #     "timestamp": time.time(),
        #     "status": "alive"
        # }
        # 
        # try:
        #     self.message_queue.put_nowait(message)
        # except queue.Full:
        #     self.logger.warning("하트비트 메시지 큐가 가득 참.")
    
    def send_connection_status(self, status: str):
        """연결 상태 메시지 전송 (메인서버 스펙 확인 후 필요시 사용)"""
        # 메인서버 프로토콜에 연결 상태 메시지가 명시되어 있지 않으므로 전송하지 않음
        print(f"🔌 연결 상태: {status} (메인서버 스펙에 없음 - 전송 생략)")
        return
        
        # 원래 코드 (주석 처리)
        # message = {
        #     "type": "connection",
        #     "status": status,
        #     "timestamp": time.time()
        # }
        # 
        # try:
        #     self.message_queue.put_nowait(message)
        # except queue.Full:
        #     pass  # 연결 상태 메시지는 중요하지 않으므로 조용히 무시
    
    def _convert_risk_level(self, risk_level: RiskLevel) -> str:
        """위험도 레벨을 Main Server 형식으로 변환"""
        return risk_level.value  # enum 값을 그대로 반환
    
    def _connect(self) -> bool:
        """Main Server에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5초 타임아웃
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            self.logger.info(f"Main Server에 연결되었습니다. ({self.host}:{self.port})")
            self.send_connection_status("connected")
            return True
            
        except Exception as e:
            self.logger.error(f"연결 실패: {e}")
            self._disconnect()
            return False
    
    def _disconnect(self):
        """연결 해제"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_message(self, message: Dict, debug: bool = True):
        """메시지 전송 - 메인서버 스펙에 맞게 순수 JSON만 전송"""
        if not self.connected:
            if debug:
                print(f"❌ 전송 실패: 연결되지 않음")
            return False
            
        try:
            # JSON 문자열로 변환하고 줄바꿈 추가 (서버에서 메시지 구분용)
            message_str = json.dumps(message, ensure_ascii=False) + "\n"
            message_bytes = message_str.encode('utf-8')
            
            if debug:
                print(f"📤 메시지 전송 시도 (메인서버 스펙):")
                print(f"   - 대상: {self.host}:{self.port}")
                print(f"   - 메시지: {message_str.strip()}")  # 줄바꿈 제거해서 출력
                print(f"   - 바이트 길이: {len(message_bytes)}")
                print(f"   - 인코딩: UTF-8")
                print(f"   - 프로토콜: JSON + 줄바꿈 구분자")
            
            # JSON + 줄바꿈으로 전송 (많은 TCP 서버에서 사용하는 표준 방식)
            bytes_sent = self.socket.sendall(message_bytes)
            if debug:
                print(f"   - JSON 메시지 전송: 완료")
                print(f"✅ 메시지 전송 성공 (메인서버 스펙 준수)")
            
            return True
            
        except Exception as e:
            if debug:
                print(f"❌ 메시지 전송 상세 오류:")
                print(f"   - 오류 타입: {type(e).__name__}")
                print(f"   - 오류 메시지: {e}")
                print(f"   - 연결 상태: {self.connected}")
            
            # 연결 오류 시 재연결 트리거
            self.connected = False
            return False
    
    def _sender_worker(self):
        """메시지 전송 워커 스레드 (디버깅 강화)"""
        print(f"🔄 메시지 전송 워커 시작 ({self.host}:{self.port})")
        
        while self.running:
            try:
                # 큐에서 메시지 가져오기 (1초 타임아웃)
                message = self.message_queue.get(timeout=1.0)
                
                print(f"📬 큐에서 메시지 획득: {message.get('type', 'unknown')}")
                
                # 연결되어 있으면 메시지 전송
                if self.connected:
                    success = self.send_message(message, debug=True)
                    if success:
                        print(f"✅ 메시지 전송 완료: {message.get('type', 'unknown')}")
                    else:
                        print(f"❌ 메시지 전송 실패: {message.get('type', 'unknown')}")
                        # 전송 실패 시 중요한 메시지는 다시 큐에 추가
                        if message.get("type") == "event":
                            try:
                                self.message_queue.put_nowait(message)
                                print(f"🔄 중요 메시지 재큐잉: {message.get('event', 'unknown')}")
                            except queue.Full:
                                print(f"⚠️ 재큐잉 실패 - 큐 가득참")
                else:
                    print(f"⚠️ 연결 끊어짐 - 메시지 보류: {message.get('type', 'unknown')}")
                    # 연결되지 않았으면 다시 큐에 넣기 (중요한 메시지만)
                    if message.get("type") == "event":
                        try:
                            self.message_queue.put_nowait(message)
                            print(f"🔄 연결 대기 중 - 메시지 재큐잉")
                        except queue.Full:
                            print(f"⚠️ 재큐잉 실패 - 큐 가득찬 상태")
                
                self.message_queue.task_done()
                
            except queue.Empty:
                # 타임아웃 - 정상적인 상황
                continue
            except Exception as e:
                print(f"❌ 메시지 전송 워커 치명적 오류: {e}")
                self.logger.error(f"메시지 전송 워커 오류: {e}")
        
        print(f"🛑 메시지 전송 워커 종료")
    
    def _reconnect_worker(self):
        """재연결 워커 스레드 (메인서버 프로토콜 준수)"""
        reconnect_interval = 5.0  # 5초마다 재연결 시도
        
        while self.running:
            current_time = time.time()
            
            # 연결되지 않았으면 재연결 시도
            if not self.connected:
                self.logger.info("재연결을 시도합니다...")
                if self._connect():
                    print(f"✅ 메인서버 재연결 성공: {self.host}:{self.port}")
            
            # 메인서버 프로토콜에 하트비트가 없으므로 연결 상태만 유지
            # (하트비트 전송 제거)
            
            time.sleep(reconnect_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """클라이언트 상태 정보 반환"""
        return {
            "connected": self.connected,
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "queue_size": self.message_queue.qsize(),
            "last_sent_risk": self.last_sent_risk.value if self.last_sent_risk else None,
            "last_send_time": self.last_send_time
        }


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # TCP 클라이언트 생성 및 시작
    client = BDSTCPClient(host="localhost", port=5200)
    client.start()
    
    try:
        # 테스트 메시지 전송 (메인서버 스펙에 맞춤)
        time.sleep(2)
        client.send_risk_update(RiskLevel.BR_MEDIUM)
        time.sleep(2)
        client.send_risk_update(RiskLevel.BR_HIGH)
        time.sleep(2)
        client.send_risk_update(RiskLevel.BR_LOW)
        
        # 상태 확인
        print("클라이언트 상태:", client.get_status())
        
        # 10초 대기
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    finally:
        client.stop() 