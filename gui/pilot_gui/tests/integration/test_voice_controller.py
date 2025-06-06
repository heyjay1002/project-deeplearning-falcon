#!/usr/bin/env python3
"""
Pilot GUI 음성 상호작용 컨트롤러 테스트 스크립트
"""

import sys
import os
import time

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 절대 import로 변경
from audio_io.mic_speaker_io import AudioIO
from stt.whisper_engine import WhisperSTTEngine
from query_parser.request_classifier import RequestClassifier
from request_router.request_executor import RequestExecutor
from tts.tts_engine import TTSEngine
from session_utils.session_manager import SessionManager
from models.request_response_model import VoiceInteraction, AudioData
from controller.voice_interaction_controller import VoiceInteractionController

def test_basic_functionality():
    """기본 기능 테스트"""
    print("=== Pilot GUI 음성 상호작용 컨트롤러 테스트 ===\n")
    
    try:
        # 컨트롤러 초기화
        print("1. 컨트롤러 초기화 중...")
        controller = VoiceInteractionController()
        print("✓ 컨트롤러 초기화 완료\n")
        
        # 시스템 상태 확인
        print("2. 시스템 상태 확인...")
        status = controller.get_system_status()
        for module, state in status.items():
            print(f"   {module}: {state}")
        print()
        
        # 음성 상호작용 테스트 (시뮬레이션)
        print("3. 음성 상호작용 테스트...")
        print("   주의: 실제 마이크 입력이 필요합니다.")
        print("   5초 동안 음성을 입력해주세요...")
        
        # 테스트용 콜사인
        test_callsign = "KAL123"
        
        # 음성 상호작용 실행
        interaction = controller.handle_voice_interaction(
            callsign=test_callsign,
            recording_duration=5.0
        )
        
        # 결과 출력
        print("\n=== 상호작용 결과 ===")
        summary = interaction.get_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        print("\n4. 세션 정보 확인...")
        sessions = controller.session_manager.get_active_sessions()
        print(f"   활성 세션 수: {len(sessions)}")
        
        # 통계 확인
        print("\n5. 일일 통계 확인...")
        stats = controller.session_manager.get_daily_stats()
        print(f"   오늘 총 상호작용: {stats.get('total_interactions', 0)}")
        print(f"   평균 처리 시간: {stats.get('average_processing_time', 0):.3f}초")
        
        # 컨트롤러 종료
        print("\n6. 컨트롤러 종료...")
        controller.shutdown()
        print("✓ 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def test_without_audio():
    """오디오 없이 모듈 테스트"""
    print("=== 오디오 없이 모듈 테스트 ===\n")
    
    try:
        # 각 모듈 개별 테스트
        print("1. 쿼리 파서 테스트...")
        
        classifier = RequestClassifier()
        test_queries = [
            "KAL123, 조류 위험도 확인 요청",
            "AAR456, 활주로 A 상태 점검",
            "UAL789, FOD 탐지 상태는?",
            "DLH012, 시스템 상태 확인",
            "SIA345, 비상 절차 안내 요청"
        ]
        
        for query in test_queries:
            request_code, parameters = classifier.classify(query)
            print(f"   '{query}' → {request_code}")
        
        print("\n2. 요청 실행기 테스트...")
        
        executor = RequestExecutor()
        for query in test_queries:
            request_code, parameters = classifier.classify(query)
            response = executor.process_request(request_code, parameters)
            print(f"   {request_code} → '{response[:50]}...'")
        
        print("\n3. 세션 매니저 테스트...")
        
        session_mgr = SessionManager()
        session_id = session_mgr.new_session_id()
        print(f"   새 세션 생성: {session_id}")
        
        # 가짜 상호작용 로그
        session_mgr.log_interaction(
            session_id=session_id,
            callsign="TEST123",
            stt_text="테스트 음성 인식",
            request_code="BIRD_RISK_CHECK",
            parameters={"runway": "RWY-A"},
            response_text="테스트 응답",
            processing_time=1.5,
            confidence_score=0.85
        )
        print("   ✓ 상호작용 로그 기록 완료")
        
        print("\n✓ 모듈 테스트 완료")
        
    except Exception as e:
        print(f"❌ 모듈 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def test_supported_requests():
    """지원하는 요청 유형 확인"""
    print("=== 지원하는 요청 유형 ===\n")
    
    try:
        classifier = RequestClassifier()
        requests = classifier.get_supported_requests()
        
        for i, req in enumerate(requests, 1):
            print(f"{i}. {req['code']}")
            print(f"   설명: {req['description']}")
            print(f"   키워드: {', '.join(req['keywords'][:5])}...")
            print()
        
    except Exception as e:
        print(f"❌ 요청 유형 조회 오류: {e}")

def main():
    """메인 함수"""
    print("Pilot GUI 테스트 스크립트")
    print("=" * 50)
    
    while True:
        print("\n테스트 옵션을 선택하세요:")
        print("1. 전체 기능 테스트 (마이크 필요)")
        print("2. 모듈별 테스트 (오디오 없음)")
        print("3. 지원 요청 유형 확인")
        print("4. 종료")
        
        choice = input("\n선택 (1-4): ").strip()
        
        if choice == "1":
            test_basic_functionality()
        elif choice == "2":
            test_without_audio()
        elif choice == "3":
            test_supported_requests()
        elif choice == "4":
            print("테스트를 종료합니다.")
            break
        else:
            print("잘못된 선택입니다. 다시 시도해주세요.")

if __name__ == "__main__":
    main() 