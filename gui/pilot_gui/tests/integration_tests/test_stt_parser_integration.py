#!/usr/bin/env python3
"""
STT + RequestClassifier 통합 테스트 + 구조화된 질의 시스템
실제 음성 입력을 받아서 전체 파이프라인을 테스트합니다.
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from audio_io.mic_speaker_io import AudioIO
    from stt.whisper_engine import WhisperSTTEngine
    from query_parser.request_classifier import RequestClassifier
from controller.voice_interaction_controller import (
    VoiceInteractionController, 
    create_voice_controller_with_structured_query,
    create_voice_controller_legacy
)

class IntegratedVoiceTestSuite:
    """통합 음성 테스트 스위트 - 구조화된 질의 시스템 포함"""
    
    def __init__(self, use_structured_query: bool = True, server_url: str = "http://localhost:8000"):
        """
        테스트 스위트 초기화
        
        Args:
            use_structured_query: 구조화된 질의 시스템 사용 여부
            server_url: 메인 서버 URL
        """
        self.use_structured_query = use_structured_query
        self.server_url = server_url
        
        print(f"🧪 통합 음성 테스트 스위트 초기화")
        print(f"   구조화된 질의: {'활성화' if use_structured_query else '비활성화'}")
        print(f"   서버 URL: {server_url}")
        
        # VoiceInteractionController 생성
        if use_structured_query:
            self.controller = create_voice_controller_with_structured_query(
                server_url=server_url,
                use_mock_fallback=True,  # 서버 없을 때 모의 응답 사용
                stt_model="small"
            )
        else:
            self.controller = create_voice_controller_legacy()
        
        # 테스트 결과 저장
        self.test_results = []
        self.test_stats = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0
        }
        
        print("✅ 테스트 스위트 초기화 완료")
    
    def run_single_test(self, test_name: str = "Manual Test", 
                       callsign: str = "FALCON 456", 
                       recording_duration: float = 5.0) -> Dict:
        """
        단일 음성 테스트 실행
        
        Args:
            test_name: 테스트 이름
            callsign: 항공기 콜사인
            recording_duration: 녹음 시간 (초)
            
        Returns:
            테스트 결과 딕셔너리
        """
        print(f"\n🎤 {test_name} 시작")
        print(f"   콜사인: {callsign}")
        print(f"   녹음 시간: {recording_duration}초")
        print(f"   구조화된 질의: {'활성화' if self.use_structured_query else '비활성화'}")
        print("   음성 입력을 시작하세요...")
        
        start_time = time.time()
        
        # 음성 상호작용 실행
        interaction = self.controller.handle_voice_interaction(
            callsign=callsign,
            recording_duration=recording_duration
        )
        
        total_time = time.time() - start_time
        
        # 결과 분석
        result = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "callsign": callsign,
            "session_id": interaction.session_id,
            "total_processing_time": total_time,
            "success": interaction.status == "COMPLETED",
            "structured_query_used": self.use_structured_query,
            
            # STT 결과
            "stt_text": interaction.stt_result.text if interaction.stt_result else "",
            "stt_confidence": interaction.stt_result.confidence_score if interaction.stt_result else 0.0,
            "stt_processing_time": interaction.stt_result.processing_time if interaction.stt_result else 0.0,
            
            # 분류 결과
            "request_code": interaction.pilot_request.request_code if interaction.pilot_request else "UNKNOWN",
            "parameters": interaction.pilot_request.parameters if interaction.pilot_request else {},
            "classification_confidence": interaction.pilot_request.confidence_score if interaction.pilot_request else 0.0,
            
            # 응답 결과
            "response_text": interaction.pilot_response.response_text if interaction.pilot_response else "",
            "tts_text": interaction.tts_text or "",
            
            # 오류 정보
            "error_message": interaction.error_message if hasattr(interaction, 'error_message') else None
        }
        
        # 결과 출력
        self._print_test_result(result)
        
        # 결과 저장
        self.test_results.append(result)
        self._update_stats()
        
        return result
    
    def run_continuous_test(self, num_tests: int = 5, 
                          callsign: str = "FALCON 456",
                          recording_duration: float = 5.0):
        """
        연속 테스트 실행
        
        Args:
            num_tests: 테스트 횟수
            callsign: 항공기 콜사인
            recording_duration: 녹음 시간
        """
        print(f"\n🔄 연속 테스트 시작 ({num_tests}회)")
        print("각 테스트 사이에 3초 대기합니다.")
        
        for i in range(num_tests):
            print(f"\n--- 테스트 {i+1}/{num_tests} ---")
            
            self.run_single_test(
                test_name=f"Continuous Test {i+1}",
                callsign=callsign,
                recording_duration=recording_duration
            )
            
            if i < num_tests - 1:  # 마지막 테스트가 아니면 대기
                print("⏳ 3초 대기 중...")
                time.sleep(3)
        
        print(f"\n✅ 연속 테스트 완료 ({num_tests}회)")
        self.print_summary()
    
    def test_different_request_types(self):
        """
        다양한 요청 유형 테스트
        """
        test_scenarios = [
            {
                "name": "Bird Risk Inquiry",
                "instruction": "조류 위험도 문의 (예: 'FALCON 456, bird risk check')",
                "expected_code": "BIRD_RISK_INQUIRY"
            },
            {
                "name": "Runway Alpha Status",
                "instruction": "활주로 알파 상태 문의 (예: 'FALCON 456, runway alpha status')",
                "expected_code": "RUNWAY_ALPHA_STATUS"
            },
            {
                "name": "Runway Bravo Status", 
                "instruction": "활주로 브라보 상태 문의 (예: 'FALCON 456, runway bravo status')",
                "expected_code": "RUNWAY_BRAVO_STATUS"
            },
            {
                "name": "Available Runway Inquiry",
                "instruction": "사용 가능한 활주로 문의 (예: 'FALCON 456, available runway please')",
                "expected_code": "AVAILABLE_RUNWAY_INQUIRY"
            }
        ]
        
        print(f"\n🎯 다양한 요청 유형 테스트")
        print(f"구조화된 질의: {'활성화' if self.use_structured_query else '비활성화'}")
        
        for scenario in test_scenarios:
            print(f"\n--- {scenario['name']} ---")
            print(f"지시사항: {scenario['instruction']}")
            print(f"예상 분류: {scenario['expected_code']}")
            
            input("준비되면 Enter를 누르세요...")
            
            result = self.run_single_test(
                test_name=scenario['name'],
                callsign="FALCON 456",
                recording_duration=5.0
            )
                
            # 분류 정확도 확인
            if result['request_code'] == scenario['expected_code']:
                print("✅ 분류 정확!")
            else:
                print(f"❌ 분류 오류: 예상 {scenario['expected_code']}, 실제 {result['request_code']}")
        
        print(f"\n✅ 요청 유형 테스트 완료")
        self.print_summary()
    
    def test_server_connection(self):
        """
        메인 서버 연결 테스트
        """
        print(f"\n🔗 메인 서버 연결 테스트")
        
        if not self.use_structured_query:
            print("⚠️ 구조화된 질의가 비활성화되어 있어 서버 연결 테스트를 건너뜁니다.")
            return
        
        # 서버 연결 테스트
        connection_ok = self.controller.test_main_server_connection()
        print(f"서버 연결: {'✅ 성공' if connection_ok else '❌ 실패'}")
        
        # 시스템 상태 확인
        status = self.controller.get_system_status()
        print(f"\n📊 시스템 상태:")
        for key, value in status.items():
            emoji = "✅" if value == "OPERATIONAL" or value == True else "❌" if value == "FAILED" or value == False else "ℹ️"
            print(f"   {emoji} {key}: {value}")
    
    def _print_test_result(self, result: Dict):
        """테스트 결과 출력"""
        print(f"\n📊 테스트 결과: {result['test_name']}")
        print(f"   세션 ID: {result['session_id']}")
        print(f"   성공 여부: {'✅ 성공' if result['success'] else '❌ 실패'}")
        print(f"   총 처리 시간: {result['total_processing_time']:.2f}초")
        
        if result['stt_text']:
            print(f"   🎤 STT 결과: '{result['stt_text']}'")
            print(f"   🎤 STT 신뢰도: {result['stt_confidence']:.2f}")
            print(f"   🎤 STT 처리 시간: {result['stt_processing_time']:.2f}초")
            
        if result['request_code'] != "UNKNOWN":
            print(f"   🏷️ 분류 결과: {result['request_code']}")
            print(f"   🏷️ 분류 신뢰도: {result['classification_confidence']}")
            if result['parameters']:
                print(f"   🏷️ 파라미터: {result['parameters']}")
        
        if result['response_text']:
            print(f"   💬 응답: {result['response_text']}")
        
        if result['error_message']:
            print(f"   ❌ 오류: {result['error_message']}")
    
    def _update_stats(self):
        """통계 업데이트"""
        if not self.test_results:
            return
        
        self.test_stats['total_tests'] = len(self.test_results)
        self.test_stats['successful_tests'] = sum(1 for r in self.test_results if r['success'])
        self.test_stats['failed_tests'] = self.test_stats['total_tests'] - self.test_stats['successful_tests']
        
        # 성공한 테스트들의 평균 계산
        successful_results = [r for r in self.test_results if r['success']]
        if successful_results:
            self.test_stats['avg_processing_time'] = sum(r['total_processing_time'] for r in successful_results) / len(successful_results)
            self.test_stats['avg_confidence'] = sum(r['stt_confidence'] for r in successful_results) / len(successful_results)
            
    def print_summary(self):
        """테스트 요약 출력"""
        print(f"\n📈 테스트 요약")
        print(f"   총 테스트: {self.test_stats['total_tests']}")
        print(f"   성공: {self.test_stats['successful_tests']}")
        print(f"   실패: {self.test_stats['failed_tests']}")
        
        if self.test_stats['successful_tests'] > 0:
            success_rate = (self.test_stats['successful_tests'] / self.test_stats['total_tests']) * 100
            print(f"   성공률: {success_rate:.1f}%")
            print(f"   평균 처리 시간: {self.test_stats['avg_processing_time']:.2f}초")
            print(f"   평균 STT 신뢰도: {self.test_stats['avg_confidence']:.2f}")
            
        # 구조화된 질의 사용 통계
        structured_query_used = sum(1 for r in self.test_results if r.get('structured_query_used', False))
        print(f"   구조화된 질의 사용: {structured_query_used}/{self.test_stats['total_tests']}")
    
    def save_results(self, filename: Optional[str] = None):
        """테스트 결과 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_type = "structured" if self.use_structured_query else "legacy"
            filename = f"test_results_{query_type}_{timestamp}.json"
        
        results_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "structured_query_enabled": self.use_structured_query,
                "server_url": self.server_url,
                "total_tests": len(self.test_results)
            },
            "statistics": self.test_stats,
            "test_results": self.test_results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            print(f"📁 테스트 결과 저장: {filename}")
        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")
    
    def cleanup(self):
        """리소스 정리"""
        if self.controller:
            self.controller.shutdown()
        print("🧹 테스트 스위트 정리 완료")

def main():
    """메인 함수"""
    print("🚁 dl-falcon 통합 음성 테스트 스위트")
    print("=" * 50)
    
    # 테스트 모드 선택
    print("\n테스트 모드를 선택하세요:")
    print("1. 구조화된 질의 시스템 테스트 (권장)")
    print("2. 기존 시스템 테스트")
    print("3. 두 시스템 비교 테스트")
    
    choice = input("선택 (1-3): ").strip()
    
        if choice == "1":
        # 구조화된 질의 시스템 테스트
        test_suite = IntegratedVoiceTestSuite(use_structured_query=True)
        
        print("\n구조화된 질의 시스템 테스트를 시작합니다.")
        test_suite.test_server_connection()
        
        print("\n테스트 유형을 선택하세요:")
        print("1. 단일 테스트")
        print("2. 연속 테스트 (5회)")
        print("3. 요청 유형별 테스트")
        
        test_choice = input("선택 (1-3): ").strip()
        
        if test_choice == "1":
            test_suite.run_single_test()
        elif test_choice == "2":
            test_suite.run_continuous_test(5)
        elif test_choice == "3":
            test_suite.test_different_request_types()
        
        test_suite.save_results()
        test_suite.cleanup()
        
        elif choice == "2":
        # 기존 시스템 테스트
        test_suite = IntegratedVoiceTestSuite(use_structured_query=False)
        
        print("\n기존 시스템 테스트를 시작합니다.")
        test_suite.run_continuous_test(3)
        test_suite.save_results()
        test_suite.cleanup()
        
        elif choice == "3":
        # 비교 테스트
        print("\n두 시스템 비교 테스트를 시작합니다.")
        
        # 기존 시스템 테스트
        print("\n--- 기존 시스템 테스트 ---")
        legacy_suite = IntegratedVoiceTestSuite(use_structured_query=False)
        legacy_suite.run_continuous_test(3)
        legacy_suite.save_results("legacy_test_results.json")
        
        print("\n⏳ 5초 대기 후 구조화된 질의 시스템 테스트를 시작합니다...")
        time.sleep(5)
        
        # 구조화된 질의 시스템 테스트
        print("\n--- 구조화된 질의 시스템 테스트 ---")
        structured_suite = IntegratedVoiceTestSuite(use_structured_query=True)
        structured_suite.test_server_connection()
        structured_suite.run_continuous_test(3)
        structured_suite.save_results("structured_test_results.json")
        
        # 비교 결과 출력
        print("\n📊 시스템 비교 결과")
        print("=" * 30)
        print("기존 시스템:")
        legacy_suite.print_summary()
        print("\n구조화된 질의 시스템:")
        structured_suite.print_summary()
        
        legacy_suite.cleanup()
        structured_suite.cleanup()
        
        else:
        print("❌ 잘못된 선택입니다.")
        return
    
    print("\n✅ 테스트 완료!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()