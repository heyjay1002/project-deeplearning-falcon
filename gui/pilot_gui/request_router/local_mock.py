import random
import time
from typing import Dict, Any
from datetime import datetime

class LocalMockServer:
    """
    개발 및 테스트용 로컬 모의 서버
    실제 서버가 없을 때 사용
    Confluence 문서 기반 표준 응답 코드 사용
    """
    
    def __init__(self):
        # Confluence 문서 기반 표준 응답 코드 매핑 테이블
        self.standard_response_mapping = {
            # 활주로 상태 → 표준 응답 코드 매핑
            "CLEAR": {
                "RWY-ALPHA": "RWY_A_CLEAR",
                "RWY-BRAVO": "RWY_B_CLEAR"
            },
            "BLOCKED": {
                "RWY-ALPHA": "RWY_A_BLOCKED", 
                "RWY-BRAVO": "RWY_B_BLOCKED"
            },
            "CAUTION": {
                "RWY-ALPHA": "RWY_A_BLOCKED",  # 주의 상태는 차단으로 처리
                "RWY-BRAVO": "RWY_B_BLOCKED"
            }
        }
        
        # Confluence 문서 기준 조류 위험도 로테이션 데이터
        self.bird_rotation_states = [
            {"risk_level": "LOW", "response_code": "BIRD_RISK_LOW"},
            {"risk_level": "MEDIUM", "response_code": "BIRD_RISK_MEDIUM"}, 
            {"risk_level": "HIGH", "response_code": "BIRD_RISK_HIGH"},
            {"risk_level": "LOW", "response_code": "BIRD_RISK_LOW"}  # 다시 LOW로 순환
        ]
        
        self.runway_alpha_rotation_states = [
            {"status": "CLEAR", "response_code": "RWY_A_CLEAR"},
            {"status": "BLOCKED", "response_code": "RWY_A_BLOCKED"},
            {"status": "CLEAR", "response_code": "RWY_A_CLEAR"},
            {"status": "BLOCKED", "response_code": "RWY_A_BLOCKED"}
        ]
        
        self.runway_bravo_rotation_states = [
            {"status": "BLOCKED", "response_code": "RWY_B_BLOCKED"},
            {"status": "CLEAR", "response_code": "RWY_B_CLEAR"},
            {"status": "BLOCKED", "response_code": "RWY_B_BLOCKED"},
            {"status": "CLEAR", "response_code": "RWY_B_CLEAR"}
        ]
        
        # 로테이션 인덱스 초기화
        self.bird_rotation_index = 0
        self.runway_alpha_rotation_index = 0
        self.runway_bravo_rotation_index = 0
        
        # 더 다양한 활주로 시나리오
        self.runway_data = {
            "RWY-ALPHA": {
                "status": "CLEAR",
                "risk_level": "LOW", 
                "condition": "DRY",
                "wind": "270/08KT",
                "visibility": "10KM"
            },
            "RWY-BRAVO": {
                "status": "BLOCKED",  # 초기 상태 - 차단됨
                "risk_level": "MEDIUM",
                "condition": "WET", 
                "wind": "270/12KT",  # 바람 강화
                "visibility": "8KM"
            },
            "RWY-CHARLIE": {  # 새로운 활주로 추가
                "status": "BLOCKED",
                "risk_level": "HIGH",
                "condition": "MAINTENANCE",
                "wind": "270/08KT",
                "visibility": "10KM"
            }
        }
        
        # Confluence 문서 기준 조류 위험도 시나리오
        self.risk_scenarios = [
            {
                "risk_level": "LOW",
                "response_code": "BIRD_RISK_LOW",
                "bird_count": random.randint(1, 3),
                "species": ["sparrows"],
                "areas": ["taxiway area"]
            },
            {
                "risk_level": "MEDIUM", 
                "response_code": "BIRD_RISK_MEDIUM",
                "bird_count": random.randint(4, 8),
                "species": ["seagulls", "pigeons"],
                "areas": ["runway vicinity", "approach path"]
            },
            {
                "risk_level": "HIGH",
                "response_code": "BIRD_RISK_HIGH",
                "bird_count": random.randint(10, 20),
                "species": ["geese", "eagles", "hawks"],
                "areas": ["runway vicinity", "approach path", "departure corridor"]
            }
        ]
        
        # 초기 조류 위험도 (LOW 레벨로 시작)
        self.bird_data = self.risk_scenarios[0].copy()
        self.bird_last_update = datetime.now()  # 마지막 업데이트 시간
        self.bird_update_interval = 300  # 5분마다 자동 업데이트
        
        print(f"[LocalMockServer] 🦅 조류 시나리오: {self.bird_data['risk_level']} 위험도 → {self.bird_data['response_code']}")
        print(f"[LocalMockServer] 🛬 활주로 상태: ALPHA({self.runway_data['RWY-ALPHA']['status']}), BRAVO({self.runway_data['RWY-BRAVO']['status']}), CHARLIE({self.runway_data['RWY-CHARLIE']['status']})")
        print(f"[LocalMockServer] 🔄 로테이션 모드: 각 요청마다 상태 변경")
        
    def _rotate_bird_state(self):
        """조류 위험도 로테이션"""
        self.bird_rotation_index = (self.bird_rotation_index + 1) % len(self.bird_rotation_states)
        new_state = self.bird_rotation_states[self.bird_rotation_index]
        
        old_level = self.bird_data['risk_level']
        
        # 새로운 상태로 업데이트
        self.bird_data = self.risk_scenarios[self.bird_rotation_index % len(self.risk_scenarios)].copy()
        self.bird_data['risk_level'] = new_state['risk_level']
        self.bird_data['response_code'] = new_state['response_code']
        
        print(f"[LocalMockServer] 🦅 BIRD 로테이션: {old_level} → {self.bird_data['risk_level']}")
        
    def _rotate_runway_state(self, runway_id):
        """활주로 상태 로테이션"""
        if runway_id == "RWY-ALPHA":
            self.runway_alpha_rotation_index = (self.runway_alpha_rotation_index + 1) % len(self.runway_alpha_rotation_states)
            new_state = self.runway_alpha_rotation_states[self.runway_alpha_rotation_index]
            old_status = self.runway_data["RWY-ALPHA"]["status"]
            self.runway_data["RWY-ALPHA"]["status"] = new_state["status"]
            print(f"[LocalMockServer] 🛬 RWY-ALPHA 로테이션: {old_status} → {new_state['status']}")
        elif runway_id == "RWY-BRAVO":
            self.runway_bravo_rotation_index = (self.runway_bravo_rotation_index + 1) % len(self.runway_bravo_rotation_states)
            new_state = self.runway_bravo_rotation_states[self.runway_bravo_rotation_index]
            old_status = self.runway_data["RWY-BRAVO"]["status"]
            self.runway_data["RWY-BRAVO"]["status"] = new_state["status"]
            print(f"[LocalMockServer] 🛬 RWY-BRAVO 로테이션: {old_status} → {new_state['status']}")
    
    def process_query(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        모의 질의 처리 - Confluence 문서 기준 표준 응답 코드 사용
        
        Args:
            intent: 질의 인텐트 (Confluence 문서 기준)
            parameters: 질의 파라미터
            
        Returns:
            Confluence 문서 형식의 모의 응답 데이터
        """
        if intent == "bird_risk_inquiry":
            # 매 요청마다 조류 위험도 로테이션
            self._rotate_bird_state()
            
            # Confluence 문서 기준 조류 위험도 응답
            return {
                "type": "response",
                "status": "success",
                "intent": intent,
                "response_code": self.bird_data["response_code"],  # BIRD_RISK_LOW/MEDIUM/HIGH
                "source": "main_server"
            }
            
        elif intent == "runway_alpha_status":
            # 매 요청마다 활주로 상태 로테이션
            self._rotate_runway_state("RWY-ALPHA")
            
            runway_info = self.runway_data["RWY-ALPHA"]
            status = runway_info["status"]
            response_code = "RWY_A_CLEAR" if status == "CLEAR" else "RWY_A_BLOCKED"
            
            return {
                "type": "response",
                "status": "success",
                "intent": intent,
                "response_code": response_code,  # RWY_A_CLEAR 또는 RWY_A_BLOCKED
                "source": "main_server"
            }
            
        elif intent == "runway_bravo_status":
            # 매 요청마다 활주로 상태 로테이션
            self._rotate_runway_state("RWY-BRAVO")
            
            runway_info = self.runway_data["RWY-BRAVO"]
            status = runway_info["status"]
            response_code = "RWY_B_CLEAR" if status == "CLEAR" else "RWY_B_BLOCKED"
            
            return {
                "type": "response",
                "status": "success",
                "intent": intent,
                "response_code": response_code,  # RWY_B_CLEAR 또는 RWY_B_BLOCKED
                "source": "main_server"
            }
            
        elif intent == "available_runway_inquiry":
            available_runways = [rwy for rwy, info in self.runway_data.items() if info["status"] == "CLEAR"]
            
            # Confluence 문서 기준 사용 가능한 활주로 응답 코드
            if len(available_runways) == 0:
                response_code = "NO_RUNWAYS_AVAILABLE"
            elif len(available_runways) >= 3:
                response_code = "AVAILABLE_RUNWAYS_ALL"
            elif len(available_runways) == 1:
                if "RWY-ALPHA" in available_runways:
                    response_code = "AVAILABLE_RUNWAYS_A_ONLY"
                elif "RWY-BRAVO" in available_runways:
                    response_code = "AVAILABLE_RUNWAYS_B_ONLY"
                else:
                    response_code = "AVAILABLE_RUNWAYS_A_ONLY"  # 기본값
            else:
                response_code = "AVAILABLE_RUNWAYS_ALL"  # 2개 이상이면 ALL로 처리
            
            print(f"[LocalMockServer] 🛬 사용 가능한 활주로: {available_runways} → {response_code}")
            
            return {
                "type": "response",
                "status": "success",
                "intent": intent,
                "response_code": response_code,  # Confluence 문서 기준 응답 코드
                "source": "main_server"
            }
        
        else:
            return {
                "type": "response",
                "status": "error",
                "intent": intent,
                "response_code": "UNRECOGNIZED_COMMAND",
                "source": "main_server"
            } 