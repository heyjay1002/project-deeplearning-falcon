#!/usr/bin/env python3
"""
자동 이벤트 테스트 스크립트
"""

import time
from simulator import TCPSimulator
from event_handler import EventManager

def test_event_handler(event_data):
    """테스트용 이벤트 핸들러"""
    event_name = event_data.get('event')
    result = event_data.get('result')
    timestamp = event_data.get('timestamp', '')
    print(f"[TEST] 📢 이벤트 수신: {event_name} = {result} ({timestamp})")

def main():
    print("🚀 자동 이벤트 테스트 시작")
    
    # 이벤트 매니저 생성
    event_manager = EventManager(server_host="localhost", server_port=5300, use_simulator=True)
    
    # 이벤트 핸들러 등록
    event_manager.register_handler("BR_CHANGED", test_event_handler)
    event_manager.register_handler("RWY_A_STATUS_CHANGED", test_event_handler)
    event_manager.register_handler("RWY_B_STATUS_CHANGED", test_event_handler)
    
    # 연결 시도 (시뮬레이터로 폴백)
    event_manager.connect()
    
    print("⏱️ 30초간 자동 이벤트 모니터링...")
    print("예상 이벤트:")
    print("  - 조류 위험도: 15초마다")
    print("  - 활주로 A: 20초마다")
    print("  - 활주로 B: 25초마다")
    print("-" * 50)
    
    # 30초간 대기
    time.sleep(30)
    
    print("-" * 50)
    print("✅ 테스트 완료")
    
    # 정리
    event_manager.disconnect()

if __name__ == "__main__":
    main() 