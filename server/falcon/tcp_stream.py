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
        # 비디오 통신기 참조
        self.video_communicator = None
    
    def set_video_communicator(self, video_comm):
        """비디오 통신기 설정
        Args:
            video_comm: VideoCommunicator 인스턴스
        """
        self.video_communicator = video_comm

    def run(self):
        """메인 실행 루프"""
        self.detection_server.start()
        self.gui_server.start()
        
        print("[INFO] 감지 결과 통신 시작")
        
        while self.detection_server.running:
            # 새로운 클라이언트 연결 수락
            self.detection_server.accept_client()
            self.gui_server.accept_client()
            
            # IDS로부터 데이터 수신
            messages = self.detection_server.receive_json()
            if messages:
                # 메시지 처리
                self._process_messages(messages)
            
            # GUI로부터 명령 수신
            command = self.gui_server.receive_binary()
            if command:
                try:
                    command_str = command.decode().strip()
                    if command_str.startswith('MC_'):
                        response = self._handle_command(command_str)
                        self.gui_server.send_binary_to_client(response.encode())
                except Exception as e:
                    print(f"[ERROR] 명령 처리 중 오류: {e}")
            
            time.sleep(0.01)  # CPU 사용량 감소
    
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
            # # 디버깅: 수신된 메시지 출력 ########################
            # print("\n[DEBUG] IDS로부터 수신된 TCP 메시지:")
            # print(message)#json.dumps(message, indent=2, ensure_ascii=False))
            
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
            
            # 기본 메시지 형식
            gui_msg = f"{det['object_id']},{det['class']},{center_x},{center_y},RWY_A,{timestamp}"
            
            # 사람인 경우에만 state 정보 추가
            if det['class'] == 'person':
                gui_msg += ",none"  # state 정보 추가
                
            gui_messages.append(gui_msg)
        
        # 모든 메시지를 하나의 문자열로 결합하고 맨 앞에 ME_OD: 추가
        message = "ME_OD:" + ";".join(gui_messages) + "\n"
        
        # GUI로 전송 (바이너리로 변환)
        try:
            self.gui_server.send_binary_to_client(message.encode())
        except Exception as e:
            print(f"[WARNING] GUI 전송 실패: {e}")
    
    def stop(self):
        """통신 중지"""
        print("[INFO] 감지 결과 통신 중지")
        self.detection_server.close()
        self.gui_server.close()

    def _handle_command(self, command: str) -> str:
        """GUI로부터 받은 명령 처리
        Args:
            command: 명령 문자열 (예: "MC_OD:2223")
        Returns:
            str: 응답 메시지
        """
        # 명령 파싱
        if not command.startswith('MC_'):
            return "MR_ERROR:Invalid command format\n"
        
        cmd_type = command[3:5]  # OD, MP, CA, CB
        cmd_data = command[6:] if len(command) > 6 else ""
        
        # 명령 타입별 처리
        if cmd_type == 'OD':
            return self._handle_object_detail(cmd_data)
        elif cmd_type == 'MP':
            return self._handle_map_view(cmd_data)
        elif cmd_type in ['CA', 'CB']:
            return self._handle_cctv_control(cmd_type)
        else:
            return "MR_ERROR:Unknown command type\n"
    
    def _handle_object_detail(self, object_id: str) -> str:
        """객체 상세 정보 요청 처리
        Args:
            object_id: 객체 ID
        Returns:
            str: 응답 메시지
        """
        # TODO: 객체 상세 정보 조회 로직 구현
        return f"MR_OD:OK,{object_id},FOD,[100,100],RWY_A,2025-06-05T19:21:00Z,img_{object_id}.jpg\n"
    
    def _handle_map_view(self, data: str) -> str:
        """지도 보기 요청 처리
        Args:
            data: 추가 데이터
        Returns:
            str: 응답 메시지
        """
        if not self.video_communicator:
            return "MR_ERROR:Video communicator not initialized\n"
        
        # 영상 송출 중지
        self.video_communicator.stop_video_stream()
        
        response = "MR_MP:OK\n"
        self.gui_server.send_binary_to_client(response.encode())
        return response
    
    def _handle_cctv_control(self, cctv_type: str) -> str:
        """CCTV 제어 요청 처리
        Args:
            cctv_type: CCTV 타입 (CA 또는 CB)
        Returns:
            str: 응답 메시지
        """
        if not self.video_communicator:
            return "MR_ERROR:Video communicator not initialized\n"
        
        # CCTV 타입에 따라 영상 송출 시작
        if cctv_type == 'CA':
            self.video_communicator.start_video_stream('A')
        elif cctv_type == 'CB':
            self.video_communicator.start_video_stream('B')
        
        response = f"MR_{cctv_type}:OK\n"
        self.gui_server.send_binary_to_client(response.encode())
        return response 