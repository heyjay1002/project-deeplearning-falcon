import re
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass

@dataclass
class RequestPattern:
    """요청 패턴 정의"""
    request_code: str
    keywords: List[str]
    patterns: List[str]
    description: str

class RequestClassifier:
    def __init__(self):
        """
        영어 항공 통신 요청 분류기 초기화
        """
        # 영어 항공 통신 키워드 매핑
        self.request_patterns = {
            "BIRD_RISK_CHECK": [
                "bird", "birds", "wildlife", "bird strike", "bird risk", "bird hazard",
                "bird activity", "wildlife report", "bird check"
            ],
            "RUNWAY_STATUS_CHECK": [
                "runway", "runway status", "runway condition", "runway clear", 
                "runway inspection", "runway report", "rwy", "runway check"
            ],
            "FOD_STATUS_CHECK": [
                "fod", "foreign object", "debris", "runway debris", "fod check",
                "foreign object debris", "fod report"
            ],
            "SYSTEM_STATUS_CHECK": [
                "system", "system status", "system check", "equipment", "operational",
                "system report", "status check", "falcon status"
            ],
            "EMERGENCY_PROCEDURE": [
                "emergency", "mayday", "pan pan", "urgent", "distress", "emergency procedure",
                "emergency landing", "emergency situation"
            ],
            "RUNWAY_CLOSURE_REQUEST": [
                "close runway", "runway closure", "block runway", "runway closed",
                "shut down runway", "runway out of service"
            ],
            "BIRD_ALERT_LEVEL_CHANGE": [
                "bird alert", "alert level", "bird warning", "wildlife alert",
                "change alert", "alert status", "increase alert", "decrease alert"
            ],
            "LANDING_CLEARANCE_REQUEST": [
                "landing", "land", "approach", "final approach", "cleared to land",
                "landing clearance", "request landing", "inbound", "landing permission"
            ],
            "TAKEOFF_READY": [
                "takeoff", "take off", "departure", "ready for takeoff", "cleared for takeoff",
                "departure ready", "ready to go", "outbound"
            ]
        }
        
        # 콜사인 패턴 (영어)
        self.callsign_patterns = [
            r'\b(FALCON)\s*(\d{1,4}[A-Z]?)\b',     # FALCON 123
            r'\b(KAL|AAR|ASIANA|KOREAN)\s*(\d{1,4}[A-Z]?)\b',  # 주요 항공사
            r'\b([A-Z]{2,6})\s*(\d{1,4}[A-Z]?)\b'  # 일반 콜사인
        ]
        
        # 활주로 패턴 (영어)
        self.runway_patterns = [
            r'\brunway\s*(\d{1,2}[LRC]?)\b',
            r'\brwy\s*(\d{1,2}[LRC]?)\b',
            r'\b(\d{1,2}[LRC]?)\s*runway\b',
            r'\b(\d{1,2}[LRC]?)\s*rwy\b'
        ]
    
    def classify(self, query_text: str, session_id: str = "") -> Tuple[str, Dict]:
        """
        영어 항공 통신 텍스트를 분류
        
        Args:
            query_text: 분류할 영어 텍스트
            session_id: 세션 ID
            
        Returns:
            (request_code, parameters) 튜플
        """
        if not query_text or not query_text.strip():
            return "UNKNOWN_REQUEST", {"error": "Empty request"}
        
        query_lower = query_text.lower().strip()
        print(f"[RequestClassifier] Classifying request: '{query_text}' (Session: {session_id})")
        
        # 콜사인 추출
        callsign = self._extract_callsign(query_text)
        
        # 활주로 정보 추출
        runway_info = self._extract_runway_info(query_text)
        
        # 패턴 매칭으로 요청 유형 분류
        best_match = None
        best_score = 0
        
        for request_code, keywords in self.request_patterns.items():
            # 키워드 매칭 점수 계산
            keyword_matches = sum(1 for keyword in keywords if keyword in query_lower)
            
            # 구문 매칭 (더 정확한 매칭)
            phrase_matches = 0
            for keyword in keywords:
                if len(keyword.split()) > 1:  # 구문인 경우
                    if keyword in query_lower:
                        phrase_matches += 2  # 구문 매칭에 더 높은 점수
                
            total_score = keyword_matches + phrase_matches
            
            # 특정 키워드 보너스
            if request_code == "RUNWAY_STATUS_CHECK" and "runway" in query_lower:
                total_score += 2
            elif request_code == "FOD_STATUS_CHECK" and "fod" in query_lower:
                total_score += 2
            elif request_code == "SYSTEM_STATUS_CHECK" and "system" in query_lower:
                total_score += 2
            elif request_code == "EMERGENCY_PROCEDURE" and ("emergency" in query_lower or "mayday" in query_lower):
                total_score += 3
            elif request_code == "BIRD_RISK_CHECK" and "bird" in query_lower:
                total_score += 2
            elif request_code == "LANDING_CLEARANCE_REQUEST" and ("landing" in query_lower or "land" in query_lower):
                total_score += 2
            elif request_code == "TAKEOFF_READY" and ("takeoff" in query_lower or "take off" in query_lower):
                total_score += 2
            
            # 최고 점수 업데이트
            if total_score > best_score:
                best_score = total_score
                best_match = request_code
        
        # 최소 점수 임계값 확인
        if best_match and best_score >= 1:
            parameters = {
                "original_text": query_text,
                "confidence_score": best_score,
                "matched_keywords": [kw for kw in self.request_patterns[best_match] if kw in query_lower]
            }
            
            # 콜사인 추가
            if callsign:
                parameters["callsign"] = callsign
            
            # 활주로 정보 추가
            if runway_info:
                parameters["runway"] = runway_info
            
            # 특별한 파라미터 추출
            parameters.update(self._extract_special_parameters(best_match, query_text))
            
            print(f"[RequestClassifier] Classification result: {best_match} (Score: {best_score})")
            return best_match, parameters
        
        # 매칭되지 않은 경우
        print(f"[RequestClassifier] Unknown request: '{query_text}' (Best score: {best_score})")
        return "UNKNOWN_REQUEST", {
            "original_text": query_text,
            "callsign": callsign,
            "runway": runway_info,
            "best_score": best_score
        }
    
    def _extract_callsign(self, text: str) -> Optional[str]:
        """
        텍스트에서 콜사인 추출
        """
        for pattern in self.callsign_patterns:
            match = re.search(pattern, text.upper())
            if match:
                if len(match.groups()) >= 2:
                    return f"{match.group(1)} {match.group(2)}"
                else:
                    return match.group(1)
        
        return None
    
    def _extract_runway_info(self, text: str) -> Optional[str]:
        """
        텍스트에서 활주로 정보 추출
        """
        for pattern in self.runway_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"RWY {match.group(1).upper()}"
        
        return None
    
    def _extract_special_parameters(self, request_code: str, text: str) -> Dict:
        """
        요청 유형별 특별한 파라미터 추출
        """
        params = {}
        text_lower = text.lower()
        
        if request_code == "BIRD_ALERT_LEVEL_CHANGE":
            if "increase" in text_lower or "raise" in text_lower:
                params["action"] = "increase"
            elif "decrease" in text_lower or "lower" in text_lower:
                params["action"] = "decrease"
        
        elif request_code == "RUNWAY_CLOSURE_REQUEST":
            if "immediate" in text_lower or "now" in text_lower:
                params["urgency"] = "immediate"
            elif "scheduled" in text_lower or "planned" in text_lower:
                params["urgency"] = "scheduled"
        
        elif request_code == "EMERGENCY_PROCEDURE":
            if "mayday" in text_lower:
                params["emergency_type"] = "distress"
            elif "pan pan" in text_lower:
                params["emergency_type"] = "urgency"
        
        return params
    
    def get_supported_requests(self) -> List[Dict]:
        """
        지원되는 요청 유형 목록 반환
        """
        return [
            {
                "code": request_code,
                "description": f"Aviation request: {request_code.replace('_', ' ').title()}",
                "keywords": keywords[:5]  # 처음 5개 키워드만
            }
            for request_code, keywords in self.request_patterns.items()
        ]
    
    def get_classification_stats(self) -> Dict:
        """
        분류기 통계 정보 반환
        """
        return {
            "total_patterns": len(self.request_patterns),
            "supported_languages": ["English"],
            "aviation_standard": "ICAO English",
            "pattern_types": list(self.request_patterns.keys())
        }
