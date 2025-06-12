"""
감지 결과 통신을 담당하는 DetectionCommunicator 클래스
IDS로부터 객체 검출 이벤트를 수신하고 처리
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time
from datetime import datetime

from network.tcp import TCPServer
from config import *

class DetectionCommunicator(QThread):
    """감지 결과 통신을 담당하는 클래스"""
    # 시그널 정의
    detection_received = pyqtSignal(dict)  # 검출 결과 수신 시그널
    
    def __init__(self):
        super().__init__()
        # TCP 서버 초기화 (IDS로부터 감지 결과 수신용)
        self.detection_server = TCPServer(port=TCP_PORT_IMAGE)
        # GUI 통신용 TCP 서버 초기화
        self.gui_server = TCPServer(port=TCP_PORT_ADMIN)
    
    def run(self):
        """메인 실행 루프"""
        self.detection_server.start()
        self.gui_server.start()
        
        print("[INFO] 감지 결과 통신 시작")
        
        while self.detection_server.running:
            # 새로운 클라이언트 연결 수락
            self.detection_server.accept_client()
            self.gui_server.accept_client()
            
            # 데이터 수신
            messages = self.detection_server.receive_json()
            if not messages:
                time.sleep(0.001)  # CPU 사용량 감소
                continue
            
            # 메시지 처리
            self._process_messages(messages)
    
    def _process_messages(self, messages):
        """메시지 처리
        Args:
            messages: IDS로부터 받은 메시지 목록
            형식:
            {
                "type": "event",
                "event": "object_detected",
                "camera_id": "A",
                "img_id": 1718135772191843820,  # 나노초 타임스탬프
                "detections": [
                    {
                        "object_id": 1001,
                        "class": "person",
                        "bbox": [x1, y1, x2, y2],
                        "confidence": 0.92
                    },
                    ...
                ]
            }
        """
        for message in messages:
            # 디버깅: 수신된 메시지 출력 ########################
            print("\n[DEBUG] IDS로부터 수신된 TCP 메시지:")
            print(message)#json.dumps(message, indent=2, ensure_ascii=False))
            
            if not isinstance(message, dict):
                continue
            
            # 메시지 타입 확인
            if message.get('type') != 'event' or message.get('event') != 'object_detected':
                print(f"[WARNING] 알 수 없는 메시지: {message.get('type')}, {message.get('event')}")
                continue
            
            # 이미지 ID와 검출 결과 확인
            img_id = message.get('img_id')
            if img_id is None:
                print("[WARNING] 이미지 ID 없음")
                continue
            
            # 검출 결과 처리
            detections = message.get('detections', [])
            
            # 검출 결과 전달
            detection_data = {
                'img_id': img_id,
                'detections': detections
            }
            self.detection_received.emit(detection_data)
            
            # GUI로 검출 결과 전송
            self._send_to_gui(detections)
    
    def _send_to_gui(self, detections):
        """GUI로 검출 결과 전송
        Args:
            detections: 검출 결과 리스트
        """
        if not detections:
            return
            
        # 현재 시간을 ISO 8601 형식으로 변환
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            
        # 각 검출 결과를 GUI 프로토콜 형식으로 변환
        gui_messages = []
        for det in detections:
            # bbox 중심점 계산
            x1, y1, x2, y2 = det['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # GUI 메시지 형식으로 변환 (ME_OD: 제외)
            gui_msg = f"{det['object_id']},{det['class']},{center_x},{center_y},RWY_A,{timestamp}"
            gui_messages.append(gui_msg)
        
        # 모든 메시지를 하나의 문자열로 결합하고 맨 앞에 ME_OD: 추가
        message = "ME_OD:" + ";".join(gui_messages)
        
        # GUI로 전송
        try:
            self.gui_server.send(message.encode())
        except Exception as e:
            print(f"[WARNING] GUI 전송 실패: {e}")
    
    def stop(self):
        """통신 중지"""
        print("[INFO] 감지 결과 통신 중지")
        self.detection_server.close()
        self.gui_server.close() 