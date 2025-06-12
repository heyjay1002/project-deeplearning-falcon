#!/usr/bin/env python3
"""
dl-falcon Pilot GUI 메인 실행 파일
구조화된 질의 시스템 지원
"""

import sys
import os
import argparse
import signal
import time
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from controller.voice_interaction_controller import (
    VoiceInteractionController,
    create_voice_controller_with_structured_query,
    create_voice_controller_legacy
)

class PilotGUIApplication:
    """Pilot GUI 애플리케이션 메인 클래스"""
    
    def __init__(self, use_structured_query: bool = True, 
                 server_url: str = "http://localhost:8000",
                 callsign: str = "FALCON 456"):
        """
        애플리케이션 초기화
        
        Args:
            use_structured_query: 구조화된 질의 시스템 사용 여부
            server_url: 메인 서버 URL
            callsign: 기본 콜사인
        """
        self.use_structured_query = use_structured_query
        self.server_url = server_url
        self.callsign = callsign
        self.controller: Optional[VoiceInteractionController] = None
        self.running = False
        
        print(f"🚁 dl-falcon Pilot GUI 시작")
        print(f"   구조화된 질의: {'활성화' if use_structured_query else '비활성화'}")
        print(f"   서버 URL: {server_url}")
        print(f"   기본 콜사인: {callsign}")
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self) -> bool:
        """
        시스템 초기화
        
        Returns:
            초기화 성공 여부
        """
        try:
            print("\n🔧 시스템 초기화 중...")
            
            # VoiceInteractionController 생성
            if self.use_structured_query:
                self.controller = create_voice_controller_with_structured_query(
                    server_url=self.server_url,
                    use_mock_fallback=True,
                    stt_model="small"
                )
            else:
                self.controller = create_voice_controller_legacy()
            
            # 시스템 상태 확인
            status = self.controller.get_system_status()
            print(f"\n📊 시스템 상태:")
            
            all_operational = True
            for key, value in status.items():
                if key in ["audio_io", "stt_engine", "tts_engine"]:  # 핵심 컴포넌트
                    if value != "OPERATIONAL":
                        all_operational = False
                
                emoji = "✅" if value == "OPERATIONAL" or value == True else "❌" if value == "FAILED" or value == False else "ℹ️"
                print(f"   {emoji} {key}: {value}")
            
            if not all_operational:
                print("⚠️ 일부 핵심 컴포넌트가 비활성화되어 있습니다.")
                return False
            
            # 구조화된 질의 시스템 연결 테스트
            if self.use_structured_query:
                print(f"\n🔗 메인 서버 연결 테스트...")
                connection_ok = self.controller.test_main_server_connection()
                if connection_ok:
                    print("✅ 메인 서버 연결 성공")
                else:
                    print("⚠️ 메인 서버 연결 실패 - 모의 응답 모드로 동작")
            
            print("✅ 시스템 초기화 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 시스템 초기화 실패: {e}")
            return False
    
    def run_interactive_mode(self):
        """대화형 모드 실행"""
        print(f"\n🎤 대화형 음성 인터페이스 모드")
        print("=" * 50)
        print("명령어:")
        print("  - Enter: 음성 입력 시작")
        print("  - 'status': 시스템 상태 확인")
        print("  - 'toggle': 구조화된 질의 시스템 토글")
        print("  - 'callsign <콜사인>': 콜사인 변경")
        print("  - 'help': 도움말")
        print("  - 'quit': 종료")
        print("=" * 50)
        
        self.running = True
        
        while self.running:
            try:
                print(f"\n🎯 현재 콜사인: {self.callsign}")
                print(f"🔧 구조화된 질의: {'활성화' if self.use_structured_query else '비활성화'}")
                
                user_input = input("\n명령어 입력 (Enter=음성입력): ").strip().lower()
                
                if user_input == "":
                    # 음성 입력 처리
                    self._handle_voice_input()
                
                elif user_input == "status":
                    # 시스템 상태 확인
                    self._show_system_status()
                
                elif user_input == "toggle":
                    # 구조화된 질의 시스템 토글
                    self._toggle_structured_query()
                
                elif user_input.startswith("callsign "):
                    # 콜사인 변경
                    new_callsign = user_input[9:].strip().upper()
                    if new_callsign:
                        self.callsign = new_callsign
                        print(f"✅ 콜사인 변경: {self.callsign}")
                    else:
                        print("❌ 유효한 콜사인을 입력하세요.")
                
                elif user_input == "help":
                    # 도움말
                    self._show_help()
                
                elif user_input in ["quit", "exit", "q"]:
                    # 종료
                    print("👋 시스템을 종료합니다...")
                    break
                
                else:
                    print(f"❌ 알 수 없는 명령어: {user_input}")
                    print("'help'를 입력하여 사용 가능한 명령어를 확인하세요.")
                
            except KeyboardInterrupt:
                print("\n\n⏹️ 사용자에 의해 중단되었습니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                continue
        
        self.running = False
    
    def run_continuous_mode(self, interval: float = 10.0):
        """연속 음성 입력 모드"""
        print(f"\n🔄 연속 음성 입력 모드 (간격: {interval}초)")
        print("Ctrl+C로 중단할 수 있습니다.")
        
        self.running = True
        session_count = 0
        
        while self.running:
            try:
                session_count += 1
                print(f"\n--- 세션 #{session_count} ---")
                
                # 음성 입력 처리
                interaction = self.controller.handle_voice_interaction(
                    callsign=self.callsign,
                    recording_duration=5.0
                )
                
                # 결과 요약 출력
                if interaction.status == "COMPLETED":
                    print(f"✅ 세션 완료: {interaction.session_id}")
                    if interaction.stt_result:
                        print(f"   STT: '{interaction.stt_result.text}'")
                    if interaction.pilot_request:
                        print(f"   분류: {interaction.pilot_request.request_code}")
                else:
                    print(f"❌ 세션 실패: {interaction.error_message}")
                
                # 다음 세션까지 대기
                if self.running:
                    print(f"⏳ {interval}초 대기 중...")
                    time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n⏹️ 연속 모드 중단됨")
                break
            except Exception as e:
                print(f"❌ 세션 오류: {e}")
                time.sleep(2)  # 오류 시 짧은 대기
        
        self.running = False
    
    def _handle_voice_input(self):
        """음성 입력 처리"""
        print(f"\n🎤 음성 입력 시작 (5초간)...")
        print("지금 말씀하세요!")
        
        try:
            interaction = self.controller.handle_voice_interaction(
                callsign=self.callsign,
                recording_duration=5.0
            )
            
            # 결과 출력
            print(f"\n📊 처리 결과:")
            print(f"   세션 ID: {interaction.session_id}")
            print(f"   상태: {'✅ 성공' if interaction.status == 'COMPLETED' else '❌ 실패'}")
            
            if interaction.stt_result:
                print(f"   🎤 인식된 텍스트: '{interaction.stt_result.text}'")
                print(f"   🎤 신뢰도: {interaction.stt_result.confidence_score:.2f}")
            
            if interaction.pilot_request:
                print(f"   🏷️ 요청 분류: {interaction.pilot_request.request_code}")
                if interaction.pilot_request.parameters:
                    print(f"   🏷️ 파라미터: {interaction.pilot_request.parameters}")
            
            if interaction.pilot_response:
                print(f"   💬 응답: {interaction.pilot_response.response_text}")
            
            if hasattr(interaction, 'error_message') and interaction.error_message:
                print(f"   ❌ 오류: {interaction.error_message}")
            
        except Exception as e:
            print(f"❌ 음성 처리 오류: {e}")
    
    def _show_system_status(self):
        """시스템 상태 표시"""
        print(f"\n📊 시스템 상태:")
        status = self.controller.get_system_status()
        
        for key, value in status.items():
            emoji = "✅" if value == "OPERATIONAL" or value == True else "❌" if value == "FAILED" or value == False else "ℹ️"
            print(f"   {emoji} {key}: {value}")
        
        # 지원하는 요청 유형 표시
        supported_requests = self.controller.get_supported_requests()
        if supported_requests:
            print(f"\n📋 지원하는 요청 유형:")
            for req in supported_requests[:5]:  # 처음 5개만 표시
                print(f"   - {req['code']}: {req['description']}")
            if len(supported_requests) > 5:
                print(f"   ... 총 {len(supported_requests)}개 유형 지원")
    
    def _toggle_structured_query(self):
        """구조화된 질의 시스템 토글"""
        self.use_structured_query = not self.use_structured_query
        self.controller.toggle_structured_query(self.use_structured_query)
        print(f"🔧 구조화된 질의 시스템: {'활성화' if self.use_structured_query else '비활성화'}")
    
    def _show_help(self):
        """도움말 표시"""
        print(f"\n📖 도움말")
        print("=" * 30)
        print("사용 가능한 명령어:")
        print("  Enter          - 음성 입력 시작 (5초간 녹음)")
        print("  status         - 시스템 상태 및 지원 요청 유형 확인")
        print("  toggle         - 구조화된 질의 시스템 활성화/비활성화")
        print("  callsign <콜사인> - 항공기 콜사인 변경")
        print("  help           - 이 도움말 표시")
        print("  quit           - 프로그램 종료")
        print("\n음성 입력 예시:")
        print("  'FALCON 456, bird risk check'")
        print("  'FALCON 456, runway alpha status'")
        print("  'FALCON 456, available runway please'")
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n\n⏹️ 시그널 {signum} 수신됨. 시스템을 종료합니다...")
        self.running = False
        if self.controller:
            self.controller.shutdown()
        sys.exit(0)
    
    def shutdown(self):
        """시스템 종료"""
        self.running = False
        if self.controller:
            self.controller.shutdown()
        print("✅ 시스템 종료 완료")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="dl-falcon Pilot GUI - 항공기 음성 인터페이스",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                           # 기본 설정으로 대화형 모드
  python main.py --legacy                  # 기존 시스템 사용
  python main.py --continuous              # 연속 입력 모드
  python main.py --server http://localhost:9000  # 다른 서버 URL
  python main.py --callsign "ALPHA 123"   # 다른 콜사인
        """
    )
    
    parser.add_argument(
        "--legacy", 
        action="store_true",
        help="기존 시스템 사용 (구조화된 질의 비활성화)"
    )
    
    parser.add_argument(
        "--server", 
        default="http://localhost:8000",
        help="메인 서버 URL (기본값: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--callsign", 
        default="FALCON 456",
        help="기본 항공기 콜사인 (기본값: FALCON 456)"
    )
    
    parser.add_argument(
        "--continuous", 
        action="store_true",
        help="연속 음성 입력 모드"
    )
    
    parser.add_argument(
        "--interval", 
        type=float, 
        default=10.0,
        help="연속 모드에서 입력 간격 (초, 기본값: 10.0)"
    )
    
    args = parser.parse_args()
    
    # 애플리케이션 생성
    app = PilotGUIApplication(
        use_structured_query=not args.legacy,
        server_url=args.server,
        callsign=args.callsign.upper()
    )
    
    try:
        # 시스템 초기화
        if not app.initialize():
            print("❌ 시스템 초기화 실패. 프로그램을 종료합니다.")
            return 1
        
        # 실행 모드에 따라 분기
        if args.continuous:
            app.run_continuous_mode(args.interval)
        else:
            app.run_interactive_mode()
        
        # 정상 종료
        app.shutdown()
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 중단되었습니다.")
        app.shutdown()
        return 0
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        app.shutdown()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 