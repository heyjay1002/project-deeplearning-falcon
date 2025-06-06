import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class RequestExecutor:
    def __init__(self):
        """
        요청 실행기 초기화 - 시뮬레이션 데이터 설정
        """
        # 시뮬레이션용 상태 데이터
        self.runway_status = {
            "RWY-A": {"status": "CLEAR", "risk_level": "LOW", "last_check": datetime.now()},
            "RWY-B": {"status": "CLEAR", "risk_level": "LOW", "last_check": datetime.now()}
        }
        
        self.bird_activity = {
            "current_level": "MEDIUM",
            "bird_count": random.randint(3, 8),
            "species": ["소형 조류", "갈매기"],
            "last_update": datetime.now()
        }
        
        self.fod_status = {
            "detection_active": True,
            "hazards_detected": 0,
            "last_scan": datetime.now(),
            "system_health": "OPERATIONAL"
        }
        
        self.system_status = {
            "sensors": "OPERATIONAL",
            "communication": "GOOD",
            "llm_service": "ACTIVE",
            "database": "CONNECTED"
        }
    
    def process_request(self, request_code: str, parameters: Dict[str, Any], session_id: str = "") -> str:
        """
        request_code에 따라 DB 또는 로직에서 결과 조회 → 자연어 응답 구성
        
        Args:
            request_code: 요청 코드
            parameters: 요청 파라미터
            session_id: 세션 ID
            
        Returns:
            자연어 응답 텍스트
        """
        print(f"[RequestExecutor] 요청 처리: {request_code} (세션: {session_id})")
        
        # 콜사인 추출
        callsign = parameters.get("callsign", "항공기")
        
        try:
            # 요청 코드별 처리
            if request_code == "BIRD_RISK_CHECK":
                return self._handle_bird_risk_check(callsign, parameters)
            
            elif request_code == "RUNWAY_STATUS_CHECK":
                return self._handle_runway_status_check(callsign, parameters)
            
            elif request_code == "FOD_STATUS_CHECK":
                return self._handle_fod_status_check(callsign, parameters)
            
            elif request_code == "SYSTEM_STATUS_CHECK":
                return self._handle_system_status_check(callsign, parameters)
            
            elif request_code == "EMERGENCY_PROCEDURE":
                return self._handle_emergency_procedure(callsign, parameters)
            
            elif request_code == "RUNWAY_CLOSURE_REQUEST":
                return self._handle_runway_closure_request(callsign, parameters)
            
            elif request_code == "BIRD_ALERT_LEVEL_CHANGE":
                return self._handle_bird_alert_level_change(callsign, parameters)
            
            elif request_code == "LANDING_CLEARANCE_REQUEST":
                return self._handle_landing_clearance_request(callsign, parameters)
            
            elif request_code == "TAKEOFF_READY":
                return self._handle_takeoff_ready(callsign, parameters)
            
            else:
                return self._handle_unknown_request(callsign, parameters)
                
        except Exception as e:
            print(f"[RequestExecutor] 요청 처리 오류: {e}")
            return f"{callsign}, 요청 처리 중 오류가 발생했습니다. 다시 시도해 주세요."
    
    def _handle_bird_risk_check(self, callsign: str, parameters: Dict) -> str:
        """조류 위험도 확인 처리"""
        runway = parameters.get("runway", "전체 구역")
        level = self.bird_activity["current_level"]
        count = self.bird_activity["bird_count"]
        
        level_kr = {"LOW": "낮음", "MEDIUM": "보통", "HIGH": "높음"}.get(level, "알 수 없음")
        
        if runway == "전체 구역":
            return f"{callsign}, 현재 조류 활동 수준은 {level_kr}입니다. {count}마리의 소형 조류가 활주로 주변에서 관찰되고 있습니다."
        else:
            return f"{callsign}, {runway} 구역의 조류 위험도는 {level_kr}입니다. 주의하여 운항하시기 바랍니다."
    
    def _handle_runway_status_check(self, callsign: str, parameters: Dict) -> str:
        """활주로 상태 확인 처리"""
        runway = parameters.get("runway")
        
        if runway and runway in self.runway_status:
            status = self.runway_status[runway]
            status_kr = {"CLEAR": "안전", "BLOCKED": "차단됨", "CAUTION": "주의"}.get(status["status"], "알 수 없음")
            risk_kr = {"LOW": "낮음", "MEDIUM": "보통", "HIGH": "높음"}.get(status["risk_level"], "알 수 없음")
            
            return f"{callsign}, {runway}는 현재 {status_kr} 상태입니다. 위험도 {risk_kr}, 조류 활동 없음, FOD 탐지되지 않음."
        else:
            # 전체 활주로 상태
            return f"{callsign}, 활주로 A와 B 모두 안전 상태입니다. 위험도 낮음, 운항 가능합니다."
    
    def _handle_fod_status_check(self, callsign: str, parameters: Dict) -> str:
        """FOD 탐지 상태 확인 처리"""
        if self.fod_status["detection_active"]:
            hazards = self.fod_status["hazards_detected"]
            if hazards == 0:
                return f"{callsign}, FOD 탐지 시스템이 정상 작동 중입니다. 현재까지 위험한 이물질은 탐지되지 않았습니다."
            else:
                return f"{callsign}, FOD 탐지 시스템에서 {hazards}건의 이물질이 감지되었습니다. 주의가 필요합니다."
        else:
            return f"{callsign}, FOD 탐지 시스템이 현재 비활성 상태입니다. 시스템 점검이 필요합니다."
    
    def _handle_system_status_check(self, callsign: str, parameters: Dict) -> str:
        """시스템 상태 확인 처리"""
        status = self.system_status
        return (f"{callsign}, FALCON 시스템 상태: "
                f"센서 {status['sensors']}, "
                f"통신 연결 {status['communication']}, "
                f"LLM 서비스 {status['llm_service']}, "
                f"데이터베이스 {status['database']}.")
    
    def _handle_emergency_procedure(self, callsign: str, parameters: Dict) -> str:
        """비상 절차 안내 처리"""
        return (f"{callsign}, 비상 절차 안내: "
                f"1) 관제탑에 즉시 보고, "
                f"2) 해당 활주로 폐쇄, "
                f"3) 안전팀 출동 요청, "
                f"4) 상황 해결까지 대기. "
                f"추가 지원이 필요하면 알려주세요.")
    
    def _handle_runway_closure_request(self, callsign: str, parameters: Dict) -> str:
        """활주로 폐쇄 요청 처리"""
        runway = parameters.get("runway", "지정된 활주로")
        urgency = parameters.get("urgency", "일반")
        
        if urgency == "immediate":
            return f"{callsign}, {runway} 즉시 폐쇄 요청을 접수했습니다. 관제탑에 통보하고 즉시 폐쇄 절차를 진행합니다."
        else:
            return f"{callsign}, {runway} 폐쇄 요청을 접수했습니다. 관제탑에 통보하고 폐쇄 절차를 진행하겠습니다."
    
    def _handle_bird_alert_level_change(self, callsign: str, parameters: Dict) -> str:
        """조류 경보 레벨 변경 처리"""
        action = parameters.get("action", "변경")
        
        if action == "increase":
            self.bird_activity["current_level"] = "HIGH"
            return f"{callsign}, 조류 경보 레벨을 높음으로 상향 조정했습니다. 모든 항공기에 주의 경보를 발령합니다."
        elif action == "decrease":
            self.bird_activity["current_level"] = "LOW"
            return f"{callsign}, 조류 경보 레벨을 낮음으로 하향 조정했습니다."
        else:
            return f"{callsign}, 조류 경보 레벨 변경 요청을 처리했습니다."
    
    def _handle_landing_clearance_request(self, callsign: str, parameters: Dict) -> str:
        """착륙 허가 요청 처리"""
        runway = parameters.get("runway", "활주로 A")
        
        # 간단한 기상 정보 시뮬레이션
        wind_dir = random.randint(250, 290)
        wind_speed = random.randint(3, 8)
        visibility = random.choice(["10km 이상", "8km", "5km"])
        
        return (f"{callsign}, {runway} 착륙 허가합니다. "
                f"바람 {wind_dir}도 {wind_speed}노트, 시정 {visibility}. "
                f"착륙 후 유도로 A3으로 이동하세요.")
    
    def _handle_takeoff_ready(self, callsign: str, parameters: Dict) -> str:
        """이륙 준비 완료 처리"""
        runway = parameters.get("runway", "활주로 B")
        
        return (f"{callsign}, {runway} 이륙 허가합니다. "
                f"이륙 후 좌선회하여 3000피트까지 상승하세요.")
    
    def _handle_unknown_request(self, callsign: str, parameters: Dict) -> str:
        """알 수 없는 요청 처리"""
        original_text = parameters.get("original_text", "")
        return f"{callsign}, 요청을 이해하지 못했습니다. 다시 명확하게 말씀해 주세요."
    
    def update_runway_status(self, runway: str, status: str, risk_level: str = "LOW"):
        """활주로 상태 업데이트 (외부에서 호출 가능)"""
        if runway in self.runway_status:
            self.runway_status[runway]["status"] = status
            self.runway_status[runway]["risk_level"] = risk_level
            self.runway_status[runway]["last_check"] = datetime.now()
    
    def update_bird_activity(self, level: str, count: int = None):
        """조류 활동 상태 업데이트"""
        self.bird_activity["current_level"] = level
        if count is not None:
            self.bird_activity["bird_count"] = count
        self.bird_activity["last_update"] = datetime.now()
    
    def get_current_status(self) -> Dict:
        """현재 전체 상태 반환"""
        return {
            "runway_status": self.runway_status,
            "bird_activity": self.bird_activity,
            "fod_status": self.fod_status,
            "system_status": self.system_status
        }
