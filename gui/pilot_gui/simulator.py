import random
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class TCPSimulator:
    """
    TCP 서버 시뮬레이터
    
    실제 TCP 서버의 동작을 시뮬레이션하며, 다음 용도로 사용됩니다:
    1. 서버 연결 실패 시 폴백 메커니즘
    2. 개발 및 테스트 환경
    3. 오프라인 모드 지원
    """
    
    def __init__(self):
        # TCP 프로토콜 기준 명령어 매핑
        self.command_mapping = {
            "BR_INQ": "BR_INQ",
            "RWY_A_STATUS": "RWY_A_STATUS",
            "RWY_B_STATUS": "RWY_B_STATUS", 
            "RWY_AVAIL_INQ": "RWY_AVAIL_INQ"
        }
        
        # TCP 프로토콜 기준 조류 위험도 로테이션 데이터
        self.bird_rotation_states = [
            {"risk_level": "LOW", "result": "BR_LOW"},
            {"risk_level": "MEDIUM", "result": "BR_MEDIUM"}, 
            {"risk_level": "HIGH", "result": "BR_HIGH"},
            {"risk_level": "LOW", "result": "BR_LOW"}  # 다시 LOW로 순환
        ]
        
        # TCP 프로토콜 기준 활주로 상태 로테이션 (CLEAR/WARNING)
        self.runway_alpha_rotation_states = [
            {"status": "CLEAR", "result": "CLEAR"},
            {"status": "WARNING", "result": "WARNING"},
            {"status": "CLEAR", "result": "CLEAR"},
            {"status": "WARNING", "result": "WARNING"}
        ]
        
        self.runway_bravo_rotation_states = [
            {"status": "WARNING", "result": "WARNING"},
            {"status": "CLEAR", "result": "CLEAR"},
            {"status": "WARNING", "result": "WARNING"},
            {"status": "CLEAR", "result": "CLEAR"}
        ]
        
        # 로테이션 인덱스 초기화
        self.bird_rotation_index = 0
        self.runway_alpha_rotation_index = 0
        self.runway_bravo_rotation_index = 0
        
        # 활주로 데이터 (TCP 프로토콜 기준)
        self.runway_data = {
            "RWY-ALPHA": {
                "status": "CLEAR",
                "risk_level": "LOW", 
                "condition": "DRY",
                "wind": "270/08KT",
                "visibility": "10KM"
            },
            "RWY-BRAVO": {
                "status": "WARNING",  # 초기 상태 - 경고
                "risk_level": "MEDIUM",
                "condition": "WET", 
                "wind": "270/12KT",
                "visibility": "8KM"
            }
        }
        
        # TCP 프로토콜 기준 조류 위험도 시나리오
        self.risk_scenarios = [
            {
                "risk_level": "LOW",
                "result": "BR_LOW",
                "bird_count": random.randint(1, 3),
                "species": ["sparrows"],
                "areas": ["taxiway area"]
            },
            {
                "risk_level": "MEDIUM", 
                "result": "BR_MEDIUM",
                "bird_count": random.randint(4, 8),
                "species": ["seagulls", "pigeons"],
                "areas": ["runway vicinity", "approach path"]
            },
            {
                "risk_level": "HIGH",
                "result": "BR_HIGH",
                "bird_count": random.randint(10, 20),
                "species": ["geese", "eagles", "hawks"],
                "areas": ["runway vicinity", "approach path", "departure corridor"]
            }
        ]
        
        # 초기 조류 위험도 (LOW 레벨로 시작)
        self.bird_data = self.risk_scenarios[0].copy()
        self.bird_last_update = datetime.now()
        
        print(f"[TCPSimulator] 🦅 조류 시나리오: {self.bird_data['risk_level']} 위험도 → {self.bird_data['result']}")
        print(f"[TCPSimulator] 🛬 활주로 상태: ALPHA({self.runway_data['RWY-ALPHA']['status']}), BRAVO({self.runway_data['RWY-BRAVO']['status']})")
        print(f"[TCPSimulator] 🔄 TCP 프로토콜 기준 로테이션 모드")
    
    def _rotate_bird_state(self):
        """조류 위험도 로테이션 (TCP 프로토콜 기준)"""
        self.bird_rotation_index = (self.bird_rotation_index + 1) % len(self.bird_rotation_states)
        new_state = self.bird_rotation_states[self.bird_rotation_index]
        
        old_level = self.bird_data['risk_level']
        
        # 새로운 상태로 업데이트
        self.bird_data = self.risk_scenarios[self.bird_rotation_index % len(self.risk_scenarios)].copy()
        self.bird_data['risk_level'] = new_state['risk_level']
        self.bird_data['result'] = new_state['result']
        
        print(f"[TCPSimulator] 🦅 BIRD 로테이션: {old_level} → {self.bird_data['risk_level']} ({self.bird_data['result']})")
    
    def _rotate_runway_state(self, runway_id):
        """활주로 상태 로테이션 (TCP 프로토콜 기준)"""
        if runway_id == "RWY-ALPHA":
            self.runway_alpha_rotation_index = (self.runway_alpha_rotation_index + 1) % len(self.runway_alpha_rotation_states)
            new_state = self.runway_alpha_rotation_states[self.runway_alpha_rotation_index]
            old_status = self.runway_data["RWY-ALPHA"]["status"]
            self.runway_data["RWY-ALPHA"]["status"] = new_state["status"]
            print(f"[TCPSimulator] 🛬 RWY-ALPHA 로테이션: {old_status} → {new_state['status']} ({new_state['result']})")
        elif runway_id == "RWY-BRAVO":
            self.runway_bravo_rotation_index = (self.runway_bravo_rotation_index + 1) % len(self.runway_bravo_rotation_states)
            new_state = self.runway_bravo_rotation_states[self.runway_bravo_rotation_index]
            old_status = self.runway_data["RWY-BRAVO"]["status"]
            self.runway_data["RWY-BRAVO"]["status"] = new_state["status"]
            print(f"[TCPSimulator] 🛬 RWY-BRAVO 로테이션: {old_status} → {new_state['status']} ({new_state['result']})")
    
    def process_query(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        TCP 프로토콜 기준 시뮬레이션 질의 처리
        
        Args:
            intent: 질의 인텐트 (bird_risk_inquiry, runway_alpha_status 등)
            parameters: 질의 파라미터
            
        Returns:
            TCP 프로토콜 형식의 시뮬레이션 응답 데이터
        """
        if intent == "bird_risk_inquiry":
            # 매 요청마다 조류 위험도 로테이션
            self._rotate_bird_state()
            
            # TCP 프로토콜 기준 조류 위험도 응답
            return {
                "type": "response",
                "command": "BR_INQ",
                "result": self.bird_data["result"],  # BR_HIGH, BR_MEDIUM, BR_LOW
                "source": "simulator"
            }
            
        elif intent == "runway_alpha_status":
            # 매 요청마다 활주로 상태 로테이션
            self._rotate_runway_state("RWY-ALPHA")
            
            runway_info = self.runway_data["RWY-ALPHA"]
            status = runway_info["status"]
            result = "CLEAR" if status == "CLEAR" else "WARNING"
            
            return {
                "type": "response",
                "command": "RWY_A_STATUS",
                "result": result,  # CLEAR 또는 WARNING
                "source": "simulator"
            }
            
        elif intent == "runway_bravo_status":
            # 매 요청마다 활주로 상태 로테이션
            self._rotate_runway_state("RWY-BRAVO")
            
            runway_info = self.runway_data["RWY-BRAVO"]
            status = runway_info["status"]
            result = "CLEAR" if status == "CLEAR" else "WARNING"
            
            return {
                "type": "response",
                "command": "RWY_B_STATUS",
                "result": result,  # CLEAR 또는 WARNING
                "source": "simulator"
            }
            
        elif intent == "available_runway_inquiry":
            available_runways = [rwy for rwy, info in self.runway_data.items() if info["status"] == "CLEAR"]
            
            # TCP 프로토콜 기준 사용 가능한 활주로 응답 (ALL/A_ONLY/B_ONLY/NONE)
            if len(available_runways) == 0:
                result = "NONE"
            elif len(available_runways) >= 2:
                result = "ALL"
            elif len(available_runways) == 1:
                if "RWY-ALPHA" in available_runways:
                    result = "A_ONLY"
                elif "RWY-BRAVO" in available_runways:
                    result = "B_ONLY"
                else:
                    result = "A_ONLY"  # 기본값
            else:
                result = "ALL"
            
            print(f"[TCPSimulator] 🛬 사용 가능한 활주로: {available_runways} → {result}")
            
            return {
                "type": "response",
                "command": "RWY_AVAIL_INQ",
                "result": result,  # TCP 프로토콜 기준 응답 (ALL/A_ONLY/B_ONLY/NONE)
                "source": "simulator"
            }
        
        else:
            return {
                "type": "response",
                "command": "UNKNOWN",
                "result": "UNRECOGNIZED_COMMAND",
                "source": "simulator"
            }
    
    def send_command(self, command: str) -> Tuple[bool, Dict[str, Any]]:
        """
        TCP 클라이언트 호환성을 위한 명령어 처리 메서드
        
        Args:
            command: TCP 명령어 (BIRD_RISK_INQUIRY, RUNWAY_ALPHA_STATUS 등)
            
        Returns:
            (성공 여부, 응답 데이터) 튜플
        """
        # 명령어를 인텐트로 변환
        intent_mapping = {
            "BR_INQ": "bird_risk_inquiry",
            "RWY_A_STATUS": "runway_alpha_status",
            "RWY_B_STATUS": "runway_bravo_status",
            "RWY_AVAIL_INQ": "available_runway_inquiry"
        }
        
        intent = intent_mapping.get(command, "unknown")
        
        try:
            response = self.process_query(intent, {})
            return True, response
        except Exception as e:
            print(f"[TCPSimulator] ❌ 명령어 처리 오류: {e}")
            return False, {
                "type": "response",
                "command": command,
                "result": "ERROR",
                "source": "simulator",
                "error": str(e)
            }
    
    def generate_event(self, event_type: str) -> Optional[Dict[str, Any]]:
        """
        이벤트 생성
        
        Args:
            event_type: 이벤트 타입 (BR_CHANGED, RWY_A_STATUS_CHANGED 등)
            
        Returns:
            이벤트 데이터 또는 None
        """
        if event_type == "BR_CHANGED":
            self._rotate_bird_state()
            return {
                "type": "event",
                "event": "BR_CHANGED",
                "result": self.bird_data["result"],
                "timestamp": datetime.now().isoformat()
            }
        elif event_type == "RWY_A_STATUS_CHANGED":
            self._rotate_runway_state("RWY-ALPHA")
            return {
                "type": "event",
                "event": "RWY_A_STATUS_CHANGED",
                "result": self.runway_data["RWY-ALPHA"]["status"],
                "timestamp": datetime.now().isoformat()
            }
        elif event_type == "RWY_B_STATUS_CHANGED":
            self._rotate_runway_state("RWY-BRAVO")
            return {
                "type": "event",
                "event": "RWY_B_STATUS_CHANGED",
                "result": self.runway_data["RWY-BRAVO"]["status"],
                "timestamp": datetime.now().isoformat()
            }
        return None 