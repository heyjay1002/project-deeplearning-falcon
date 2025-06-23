"""
감지 결과 통신을 담당하는 DetectionCommunicator 클래스
IDS로부터 객체 검출 이벤트를 수신하고 처리
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time
from datetime import datetime
import os
import json

from network.tcp import TCPServer
from config import *
import config
from db.repository import DetectionRepository
import pymysql

class RunwayStatus:
    """활주로 상태 관리 클래스"""
    def __init__(self):
        # 활주로별 상태
        self.runway_a_status = 'CLEAR'  # CLEAR, WARNING
        self.runway_b_status = 'CLEAR'  # CLEAR, WARNING
        
        # 이전 상태 (변경 감지용)
        self.previous_a_status = 'CLEAR'
        self.previous_b_status = 'CLEAR'
    
    def update_runway_status(self, detections):
        """객체 감지 결과로 활주로 상태 업데이트"""
        # 활주로별 객체 존재 여부만 확인
        runway_a_has_objects = False
        runway_b_has_objects = False
        
        for det in detections:
            area_name = det.get('area_name', '')
            
            if 'RWY_A' in area_name:
                runway_a_has_objects = True
            if 'RWY_B' in area_name:
                runway_b_has_objects = True
        
        # 활주로별 상태 결정: 객체가 있으면 WARNING, 없으면 CLEAR
        self.runway_a_status = 'WARNING' if runway_a_has_objects else 'CLEAR'
        self.runway_b_status = 'WARNING' if runway_b_has_objects else 'CLEAR'
    
    def check_status_changes(self):
        """상태 변경 감지"""
        changes = []
        
        # 활주로 A 상태 변경 감지
        if self.previous_a_status != self.runway_a_status:
            changes.append(('A', self.runway_a_status))
            self.previous_a_status = self.runway_a_status
        
        # 활주로 B 상태 변경 감지
        if self.previous_b_status != self.runway_b_status:
            changes.append(('B', self.runway_b_status))
            self.previous_b_status = self.runway_b_status
        
        return changes
    
    def get_runway_status(self, runway_id):
        """활주로 상태 반환"""
        if runway_id == 'A':
            return self.runway_a_status
        elif runway_id == 'B':
            return self.runway_b_status
        return 'CLEAR'

class DetectionCommunicator(QThread):
    """감지 결과 통신을 담당하는 클래스"""
    # 시그널 정의
    detection_received = pyqtSignal(dict)  # 검출 결과 수신 시그널
    
    def __init__(self, repository=None):
        super().__init__()
        # TCP 서버 초기화 (IDS로부터 감지 결과 수신용)
        self.detection_server = TCPServer(port=TCP_PORT_IMAGE)
        # GUI 통신용 TCP 서버 초기화
        self.gui_server = TCPServer(port=TCP_PORT_ADMIN)
        # BDS 통신용 TCP 서버 초기화
        self.bds_server = TCPServer(port=TCP_PORT_BIRD)
        # 조종사 GUI 통신용 TCP 서버 초기화
        self.pilot_server = TCPServer(port=TCP_PORT_PILOT)
        # 비디오 통신기 참조
        self.video_communicator = None
        self.area_list = self._load_area_table()
        self.repository = repository
        if self.repository:
            self.repository.set_save_complete_callback(self.send_first_detection_to_gui)
            
        # IDS 클라이언트 관리
        self.sent_clients = set()
        
        # 활주로 상태 관리
        self.runway_status = RunwayStatus()
            
        # 로그 디렉토리 설정
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.ids_log_file = os.path.join(self.log_dir, f'ids_tcp_{datetime.now().strftime("%Y%m%d")}.log')
        self.gui_log_file = os.path.join(self.log_dir, f'gui_tcp_{datetime.now().strftime("%Y%m%d")}.log')
        self.bds_log_file = os.path.join(self.log_dir, f'bds_tcp_{datetime.now().strftime("%Y%m%d")}.log')
        self.pilot_log_file = os.path.join(self.log_dir, f'pilot_tcp_{datetime.now().strftime("%Y%m%d")}.log')
        print(f"[INFO] IDS TCP 로그 파일: {self.ids_log_file}")
        print(f"[INFO] GUI TCP 로그 파일: {self.gui_log_file}")
        print(f"[INFO] BDS TCP 로그 파일: {self.bds_log_file}")
        print(f"[INFO] Pilot TCP 로그 파일: {self.pilot_log_file}")
    
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
        self.bds_server.start()
        self.pilot_server.start()
        
        print("[INFO] 감지 결과 통신 시작")
        
        while self.detection_server.running:
            # 새로운 클라이언트 연결 수락
            self.detection_server.accept_client()
            self.gui_server.accept_client()
            self.bds_server.accept_client()
            self.pilot_server.accept_client()
            
            # 새로운 IDS 클라이언트에게 모드 설정 명령 전송
            self._send_mode_to_new_ids_clients()

            # IDS로부터 데이터 수신
            messages = self.detection_server.receive_json()
            if messages:
                # 메시지 처리
                self._process_messages(messages)
            
            # BDS로부터 데이터 수신
            bds_messages = self.bds_server.receive_json()
            if bds_messages:
                # BDS 메시지 처리
                self._process_bds_messages(bds_messages)
            
            # 조종사 GUI로부터 데이터 수신
            pilot_messages = self.pilot_server.receive_json()
            if pilot_messages:
                # 조종사 GUI 메시지 처리
                self._process_pilot_messages(pilot_messages)
            
            # GUI로부터 명령 수신
            command = self.gui_server.receive_binary()
            if command:
                try:
                    command_str = command.decode().strip()
                    self._log_gui_communication("RECV", command_str) # 수신 로그
                    if command_str.startswith('MC_'):
                        response = self._handle_command(command_str)
                        
                        # 응답 로깅 및 전송
                        if response:
                            # 상세 정보 요청(OD)의 응답은 헤더와 바이너리로 나뉨
                            if isinstance(response, tuple) and len(response) == 2:
                                header, binary_data = response
                                self._log_gui_communication("SEND", header.strip())
                                self._log_gui_communication("SEND", f"[Binary Data of size {len(binary_data)}]")
                                # 헤더와 바이너리를 '$$'로 결합하여 전송
                                final_response = header.encode('utf-8') + b'$$' + binary_data
                                self.gui_server.send_binary_to_client(final_response)
                            # 그 외 일반 응답 처리
                            elif isinstance(response, str):
                                self._log_gui_communication("SEND", response.strip())
                                self.gui_server.send_binary_to_client(response.encode())
                            elif isinstance(response, bytes):
                                self._log_gui_communication("SEND", "[Binary Data]")
                                self.gui_server.send_binary_to_client(response)
                except Exception as e:
                    error_msg = f"명령 처리 중 오류: {e}"
                    print(f"[ERROR] {error_msg}")
                    self._log_gui_communication("ERROR", error_msg)
            
            time.sleep(0.01)  # CPU 사용량 감소
    
    def _send_mode_to_new_ids_clients(self):
        """새로 연결된 IDS 클라이언트에게 모드 설정 명령을 보냅니다."""
        current_client_sockets = set(self.detection_server.client_sockets)
        new_clients = current_client_sockets - self.sent_clients

        for client_socket in new_clients:
            try:
                command = {
                    "type": "command",
                    "command": "set_mode_object"
                }
                json_str = json.dumps(command, ensure_ascii=False) + '\n'
                encoded_data = json_str.encode('utf-8')
                
                client_socket.sendall(encoded_data)
                
                self.sent_clients.add(client_socket)
                print(f"[INFO] IDS 클라이언트 {client_socket.getpeername()}에 'set_mode_object' 명령 전송 완료")

            except Exception as e:
                print(f"[ERROR] IDS 클라이언트에 모드 설정 명령 전송 실패: {e}")
        
        # 연결 종료된 클라이언트를 집합에서 제거
        self.sent_clients &= current_client_sockets

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
            # TCP 로그 저장
            try:
                log_entry = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'message': message
                }
                with open(self.ids_log_file, 'a', encoding='utf-8') as f:
                    json.dump(log_entry, f, ensure_ascii=False)
                    f.write('\n')
            except Exception as e:
                print(f"[ERROR] TCP 로그 저장 실패: {e}")
            
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
            
            # 프레임 크기 정보 필요
            frame_width = config.frame_width
            frame_height = config.frame_height
            for det in detections:
                bbox = det.get('bbox', None)
                if bbox and len(bbox) == 4 and frame_width and frame_height:
                    x1, y1, x2, y2 = bbox
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    map_x, map_y, norm_x, norm_y = self.convert_to_map_coords(center_x, center_y, frame_width, frame_height)
                    area_id = self.find_area_id(norm_x, norm_y)
                    det['map_x'] = map_x
                    det['map_y'] = map_y
                    det['area_id'] = area_id
                else:
                    det['map_x'] = None
                    det['map_y'] = None
                    det['area_id'] = None
            
            # 검출 결과 전달
            detection_data = {
                'img_id': img_id,
                'detections': detections
            }
            self.detection_received.emit(detection_data)
            
            # 활주로 상태 업데이트
            self.runway_status.update_runway_status(detections)
            
            # 활주로 상태 변경 알림 전송
            status_changes = self.runway_status.check_status_changes()
            for runway_id, status in status_changes:
                self._send_runway_status_change(runway_id, status)      # 조종사 GUI
                self._send_runway_status_to_admin(runway_id, status)    # 관제사 GUI
            
            # GUI로 검출 결과 전송
            self._send_to_gui(detections)
    
    def _send_to_gui(self, detections):
        """GUI로 검출 결과 전송
        Args:
            detections: 검출 결과 리스트
        """
        if not detections:
            return
            
        # 각 검출 결과를 GUI 프로토콜 형식으로 변환
        gui_messages = []
        for det in detections:
            map_x = det.get('map_x')
            map_y = det.get('map_y')
            area_id = det.get('area_id')
            area_name = self.area_id_to_name.get(area_id, 'UNKNOWN') if area_id is not None else 'UNKNOWN'
            gui_msg = f"{det['object_id']},{det['class'].upper()},{int(map_x) if map_x is not None else -1},{int(map_y) if map_y is not None else -1},{area_name}"
            if det['class'].upper() == 'PERSON':
                gui_msg += ",none"  # state 정보 추가
            gui_messages.append(gui_msg)
        # 모든 메시지를 하나의 문자열로 결합하고 맨 앞에 ME_OD: 추가
        message = "ME_OD:" + ";".join(gui_messages) + "\n"
        # GUI로 전송 (바이너리로 변환)
        try:
            self.gui_server.send_binary_to_client(message.encode())
        except Exception as e:
            print(f"[WARNING] GUI 전송 실패: {e}")
    
    def _process_bds_messages(self, messages):
        """BDS 메시지 처리
        Args:
            messages: BDS로부터 받은 메시지 목록
            형식:
            {
                "type": "event",
                "event": "BR_CHANGED",
                "result": "BR_HIGH"  // 또는 "BR_MEDIUM", "BR_LOW"
            }
        """
        for message in messages:
            # BDS TCP 로그 저장
            try:
                log_entry = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'message': message
                }
                with open(self.bds_log_file, 'a', encoding='utf-8') as f:
                    json.dump(log_entry, f, ensure_ascii=False)
                    f.write('\n')
            except Exception as e:
                print(f"[ERROR] BDS TCP 로그 저장 실패: {e}")
            
            if not isinstance(message, dict):
                continue
            
            # 메시지 타입 확인
            if message.get('type') != 'event' or message.get('event') != 'BR_CHANGED':
                print(f"[WARNING] 알 수 없는 BDS 메시지: {message.get('type')}, {message.get('event')}")
                continue
            
            # 조류 위험도 확인
            risk_level = message.get('result')
            if risk_level not in ['BR_HIGH', 'BR_MEDIUM', 'BR_LOW']:
                print(f"[WARNING] 알 수 없는 조류 위험도: {risk_level}")
                continue
            
            print(f"[INFO] 조류 위험도 변경: {risk_level}")
            
            # 현재 조류 위험도 저장
            self.current_bird_risk = risk_level
            
            # GUI로 조류 위험도 전송
            self._send_bird_risk_to_gui(risk_level)
            
            # 조종사 GUI로 조류 위험도 변경 알림 전송
            self._send_bird_risk_to_pilot(risk_level)
    
    def _send_bird_risk_to_gui(self, risk_level):
        """GUI로 조류 위험도 전송
        Args:
            risk_level: 조류 위험도 ('BR_HIGH', 'BR_MEDIUM', 'BR_LOW')
        """
        # 위험도 레벨을 숫자로 변환 # 별도로 0(LOW), 1(MEDIUM), 2(HIGH)
        level_map = {
            'BR_HIGH': '2',
            'BR_MEDIUM': '1', 
            'BR_LOW': '0'
        }
        
        level_number = level_map.get(risk_level, '0')
        message = f"ME_BR:{level_number}\n"
        
        # GUI로 전송 (바이너리로 변환)
        try:
            self.gui_server.send_binary_to_client(message.encode())
            print(f"[INFO] 조류 위험도 전송 완료: {risk_level} -> {level_number}")
        except Exception as e:
            print(f"[WARNING] 조류 위험도 전송 실패: {e}")
    
    def _send_bird_risk_to_pilot(self, risk_level):
        """조종사 GUI로 조류 위험도 변경 알림 전송
        Args:
            risk_level: 조류 위험도 ('BR_HIGH', 'BR_MEDIUM', 'BR_LOW')
        """
        message = {
            "type": "event",
            "event": "BR_CHANGED",
            "result": risk_level
        }
        
        try:
            self.pilot_server.send_to_client(message)
            print(f"[INFO] 조종사 GUI로 조류 위험도 변경 알림 전송: {risk_level}")
        except Exception as e:
            print(f"[WARNING] 조종사 GUI 조류 위험도 알림 전송 실패: {e}")
    
    def _process_pilot_messages(self, messages):
        """조종사 GUI 메시지 처리
        Args:
            messages: 조종사 GUI로부터 받은 메시지 목록
            형식:
            {
                "type": "command",
                "command": "BR_INQ"  // 또는 "RWY_A_STATUS", "RWY_B_STATUS", "RWY_AVAIL_INQ"
            }
        """
        for message in messages:
            # 조종사 GUI TCP 로그 저장
            try:
                log_entry = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'message': message
                }
                with open(self.pilot_log_file, 'a', encoding='utf-8') as f:
                    json.dump(log_entry, f, ensure_ascii=False)
                    f.write('\n')
            except Exception as e:
                print(f"[ERROR] 조종사 GUI TCP 로그 저장 실패: {e}")
            
            if not isinstance(message, dict):
                continue
            
            # 메시지 타입 확인
            if message.get('type') != 'command':
                print(f"[WARNING] 알 수 없는 조종사 GUI 메시지 타입: {message.get('type')}")
                continue
            
            # 명령 처리
            command = message.get('command')
            if command == 'BR_INQ':
                self._handle_bird_risk_inquiry()
            elif command == 'RWY_A_STATUS':
                self._handle_runway_a_status_inquiry()
            elif command == 'RWY_B_STATUS':
                self._handle_runway_b_status_inquiry()
            elif command == 'RWY_AVAIL_INQ':
                self._handle_runway_availability_inquiry()
            else:
                print(f"[WARNING] 알 수 없는 조종사 GUI 명령: {command}")
    
    def _handle_bird_risk_inquiry(self):
        """조류 위험도 조회 처리"""
        # 현재 조류 위험도 (임시로 BDS에서 받은 최신 값 사용)
        current_risk = getattr(self, 'current_bird_risk', 'BR_LOW')
        
        response = {
            "type": "response",
            "command": "BR_INQ",
            "result": current_risk
        }
        
        try:
            self.pilot_server.send_to_client(response)
            print(f"[INFO] 조류 위험도 응답 전송: {current_risk}")
        except Exception as e:
            print(f"[WARNING] 조류 위험도 응답 전송 실패: {e}")
    
    def _handle_runway_a_status_inquiry(self):
        """활주로 A 상태 조회 처리"""
        # 활주로 A 상태 판단 (객체 감지 + 조류 위험도 종합)
        status = self.runway_status.get_runway_status('A')
        
        response = {
            "type": "response",
            "command": "RWY_A_STATUS",
            "result": status
        }
        
        try:
            self.pilot_server.send_to_client(response)
            print(f"[INFO] 활주로 A 상태 응답 전송: {status}")
        except Exception as e:
            print(f"[WARNING] 활주로 A 상태 응답 전송 실패: {e}")
    
    def _handle_runway_b_status_inquiry(self):
        """활주로 B 상태 조회 처리"""
        # 활주로 B 상태 판단 (객체 감지 + 조류 위험도 종합)
        status = self.runway_status.get_runway_status('B')
        
        response = {
            "type": "response",
            "command": "RWY_B_STATUS",
            "result": status
        }
        
        try:
            self.pilot_server.send_to_client(response)
            print(f"[INFO] 활주로 B 상태 응답 전송: {status}")
        except Exception as e:
            print(f"[WARNING] 활주로 B 상태 응답 전송 실패: {e}")
    
    def _handle_runway_availability_inquiry(self):
        """사용 가능한 활주로 조회 처리"""
        # 활주로 A, B 상태 확인
        status_a = self.runway_status.get_runway_status('A')
        status_b = self.runway_status.get_runway_status('B')
        
        # 사용 가능한 활주로 판단
        if status_a == 'CLEAR' and status_b == 'CLEAR':
            availability = 'ALL'
        elif status_a == 'CLEAR':
            availability = 'A_ONLY'
        elif status_b == 'CLEAR':
            availability = 'B_ONLY'
        else:
            availability = 'NONE'
        
        response = {
            "type": "response",
            "command": "RWY_AVAIL_INQ",
            "result": availability
        }
        
        try:
            self.pilot_server.send_to_client(response)
            print(f"[INFO] 사용 가능한 활주로 응답 전송: {availability}")
        except Exception as e:
            print(f"[WARNING] 사용 가능한 활주로 응답 전송 실패: {e}")
    
    def stop(self):
        """통신 중지"""
        print("[INFO] 감지 결과 통신 중지")
        self.detection_server.close()
        self.gui_server.close()
        self.bds_server.close()
        self.pilot_server.close()

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
    
    def _handle_object_detail(self, object_id: str) -> bytes:
        """객체 상세 정보 요청 처리.
        성공 시 (헤더, 이미지 바이너리) 튜플을 반환.
        실패 시 에러 메시지(bytes)를 반환.
        """
        # 1. object_id 유효성 검사
        try:
            object_id_int = int(object_id)
        except (ValueError, TypeError):
            return b"MR_OD:ERR,1\n"
        
        # 2. repository 초기화 확인 및 DB 조회
        if not self.repository:
            return b"MR_OD:ERR,2\n"  # Repository 미초기화 오류
        
        event_data = self.repository.get_event_by_object_id(object_id_int)
        
        if not event_data:
            return b"MR_OD:ERR,3\n" # 객체 정보 없음 오류
        
        # 3. event_data 분석 및 이미지 경로 확인
        img_path = event_data.get('img_path')
        if not img_path:
            return b"MR_OD:ERR,4\n" # 이미지 경로 정보 없음
            
        object_type = event_data.get('class', 'UNKNOWN')
        area = event_data.get('zone', 'UNKNOWN')
        timestamp = event_data.get('timestamp')
        
        # 4. 이미지 파일 처리
        try:
            full_img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), img_path)
            
            if not os.path.exists(full_img_path):
                print(f"[ERROR] 이미지 파일 없음: {full_img_path}")
                return b"MR_OD:ERR,5\n"

            img_size = os.path.getsize(full_img_path)
            with open(full_img_path, 'rb') as f:
                img_data = f.read()

        except Exception as e:
            print(f"[ERROR] 이미지 파일 처리 오류: {e}")
            return b"MR_OD:ERR,5\n"

        # 5. 최종 응답 생성
        timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ') if timestamp else ""

        # 헤더 생성 (개행 문자 없음)
        response_header = f"MR_OD:OK,{object_id_int},{object_type},{area},{timestamp_str},{img_size}"
        
        # 헤더(문자열)와 이미지(바이너리)를 튜플로 반환
        return (response_header, img_data)
    
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
        return response

    def convert_to_map_coords(self, center_x, center_y, frame_width, frame_height):
        """bbox 중심점 → 맵 좌표 변환
        Args:
            center_x (float): bbox 중심 x (픽셀)
            center_y (float): bbox 중심 y (픽셀)
            frame_width (int): 프레임 가로 크기
            frame_height (int): 프레임 세로 크기
        Returns:
            (float, float, float, float): (map_x, map_y, norm_x, norm_y)
        """
        norm_x = center_x / frame_width
        norm_y = center_y / frame_height
        map_x = norm_x * config.MAP_WIDTH
        map_y = norm_y * config.MAP_HEIGHT
        return map_x, map_y, norm_x, norm_y

    def _load_area_table(self):
        """AREA 테이블 전체를 읽어 리스트와 area_id_to_name 딕셔너리로 반환"""
        area_list = []
        area_id_to_name = {}
        conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8'
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT area_id, area_name, x1, y1, x2, y2 FROM AREA")
                for row in cur.fetchall():
                    area = {
                        'area_id': row[0],
                        'area_name': row[1],
                        'x1': float(row[2]),
                        'y1': float(row[3]),
                        'x2': float(row[4]),
                        'y2': float(row[5])
                    }
                    area_list.append(area)
                    area_id_to_name[area['area_id']] = area['area_name']
        finally:
            conn.close()
        self.area_id_to_name = area_id_to_name
        return area_list

    def find_area_id(self, norm_x, norm_y):
        """정규화 좌표(norm_x, norm_y)에 해당하는 area_id 반환"""
        for area in self.area_list:
            if area['x1'] <= norm_x <= area['x2'] and area['y1'] <= norm_y <= area['y2']:
                return area['area_id']
        return None

    def send_first_detection_to_gui(self, detections, crop_imgs):
        """최초 감지된 객체에 대해 ME_FD 메시지 생성 및 전송 (crop_imgs 사용)"""
        if not detections or not crop_imgs or len(detections) != len(crop_imgs):
            return
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        for det, img_binary in zip(detections, crop_imgs):
            try:
                object_id = det['object_id']
                object_class = det['class'].upper()
                map_x = det.get('map_x')
                map_y = det.get('map_y')
                area_id = det.get('area_id')
                area_name = self.area_id_to_name.get(area_id, 'UNKNOWN') if area_id is not None else 'UNKNOWN'
                
                # 이미지 크기가 너무 크면 압축
                if len(img_binary) > 4000:
                    import cv2
                    import numpy as np
                    nparr = np.frombuffer(img_binary, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is not None:
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                        _, img_binary = cv2.imencode('.jpg', img, encode_param)
                        img_binary = img_binary.tobytes()
                        print(f"[INFO] 이미지 압축: object_id={object_id}, old_size={len(img_binary)}, new_size={len(img_binary)}")

                # 객체 타입에 따라 다른 메시지 포맷 사용
                if object_class == 'PERSON':
                    # 사람: timestamp,state,image_size
                    state = det.get('state', 'N')
                    gui_msg_header = f"{object_id},{object_class},{int(map_x) if map_x is not None else -1},{int(map_y) if map_y is not None else -1},{area_name},{timestamp},{state},{len(img_binary)}"
                    gui_msg = gui_msg_header.encode() + b"$$" + img_binary
                    self.gui_server.send_binary_to_client(b"ME_FD:" + gui_msg)
                    # 로그 기록 ('$$' 기준)
                    self._log_gui_communication("SEND", f"ME_FD:{gui_msg_header}")
                    self._log_gui_communication("SEND", f"[Binary Data of size {len(img_binary)}]")
                else:
                    # 비사람: timestamp,image_size
                    gui_msg_header = f"{object_id},{object_class},{int(map_x) if map_x is not None else -1},{int(map_y) if map_y is not None else -1},{area_name},{timestamp},{len(img_binary)}"
                    gui_msg = gui_msg_header.encode() + b"$$" + img_binary
                    self.gui_server.send_binary_to_client(b"ME_FD:" + gui_msg)
                    # 로그 기록 ('$$' 기준)
                    self._log_gui_communication("SEND", f"ME_FD:{gui_msg_header}")
                    self._log_gui_communication("SEND", f"[Binary Data of size {len(img_binary)}]")
            except Exception as e:
                print(f"[ERROR] ME_FD 전송 실패: {e}") 

    def _log_gui_communication(self, direction, data):
        """GUI와의 통신 내용을 파일에 로깅"""
        try:
            log_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [{direction}] {data.strip()}\n"
            with open(self.gui_log_file, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            print(f"[ERROR] GUI 로그 저장 실패: {e}") 

    def _send_runway_status_change(self, runway_id, status):
        """활주로 상태 변경 알림 전송
        Args:
            runway_id: 활주로 ID ('A' 또는 'B')
            status: 새로운 활주로 상태 ('CLEAR' 또는 'WARNING')
        """
        message = {
            "type": "event",
            "event": f"RWY_{runway_id}_STATUS_CHANGED",
            "result": status
        }
        
        try:
            self.pilot_server.send_to_client(message)
            print(f"[INFO] 활주로 {runway_id} 상태 변경 알림 전송: {status}")
        except Exception as e:
            print(f"[WARNING] 활주로 {runway_id} 상태 변경 알림 전송 실패: {e}")
    
    def _send_runway_status_to_admin(self, runway_id, status):
        """활주로 상태 변경 알림 전송 (관제사 GUI)
        Args:
            runway_id: 활주로 ID ('A' 또는 'B')
            status: 새로운 활주로 상태 ('CLEAR' 또는 'WARNING')
        """
        # 상태를 숫자로 변환
        state = '1' if status == 'WARNING' else '0'
        
        message = f"ME_R{runway_id}:{state}\n"
        
        try:
            self.gui_server.send_binary_to_client(message.encode())
            print(f"[INFO] 관제사 GUI - 활주로 {runway_id} 상태 변경: {status} -> {state}")
        except Exception as e:
            print(f"[WARNING] 관제사 GUI 활주로 상태 알림 전송 실패: {e}") 