#!/usr/bin/env python3
"""
오디오 시스템 및 TTS 볼륨 조절 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui/pilot_gui'))

def test_audio_devices():
    """오디오 장치 테스트"""
    print("🎧 오디오 장치 확인")
    print("=" * 40)
    
    try:
        import pyaudio
        
        audio = pyaudio.PyAudio()
        print(f"📊 PyAudio 버전: {pyaudio.__version__}")
        print(f"📱 총 오디오 장치 수: {audio.get_device_count()}")
        
        print("\n🎤 입력 장치 목록:")
        input_devices = []
        for i in range(audio.get_device_count()):
            try:
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(device_info)
                    print(f"  {i}: {device_info['name']} (채널: {device_info['maxInputChannels']})")
            except:
                pass
        
        print("\n🔊 출력 장치 목록:")
        output_devices = []
        for i in range(audio.get_device_count()):
            try:
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0:
                    output_devices.append(device_info)
                    print(f"  {i}: {device_info['name']} (채널: {device_info['maxOutputChannels']})")
            except:
                pass
        
        audio.terminate()
        
        if not input_devices:
            print("❌ 사용 가능한 입력 장치가 없습니다!")
            return False
        if not output_devices:
            print("❌ 사용 가능한 출력 장치가 없습니다!")
            return False
            
        print("✅ 오디오 장치 확인 완료")
        return True
        
    except Exception as e:
        print(f"❌ 오디오 장치 확인 오류: {e}")
        return False

def test_simple_tts():
    """간단한 TTS 테스트"""
    print("\n🎵 TTS 시스템 테스트")
    print("=" * 40)
    
    try:
        # pyttsx3 먼저 테스트 (더 안정적)
        print("1️⃣ pyttsx3 TTS 테스트...")
        from tts.pyttsx3_engine import TTSEngine
        
        tts = TTSEngine(volume=0.8)  # 80% 볼륨
        if tts.is_engine_ready():
            print("✅ pyttsx3 TTS 엔진 준비됨")
            print("🔊 테스트 음성 재생 중...")
            tts.speak("TTS volume test at eighty percent", blocking=True)
            
            # 볼륨 50%로 테스트
            tts.set_volume(0.5)
            print("🔊 50% 볼륨 테스트...")
            tts.speak("TTS volume test at fifty percent", blocking=True)
            
            # 음소거 테스트
            tts.set_volume(0.0)
            print("🔇 음소거 테스트 (소리 안남)...")
            tts.speak("This should be silent", blocking=True)
            
            # 볼륨 복원
            tts.set_volume(0.8)
            print("🔊 볼륨 복원 테스트...")
            tts.speak("Volume restored to eighty percent", blocking=True)
            
            return True
        else:
            print("❌ pyttsx3 TTS 엔진 초기화 실패")
            return False
            
    except Exception as e:
        print(f"❌ TTS 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mic_level():
    """마이크 레벨 테스트"""
    print("\n🎤 마이크 레벨 테스트")
    print("=" * 40)
    
    try:
        from audio_io.mic_speaker_io import AudioIO
        import time
        import numpy as np
        
        # 기본 마이크로 AudioIO 생성
        audio_io = AudioIO.create_with_best_mic()
        print("✅ 마이크 초기화 완료")
        
        print("🎙️ 5초간 말해보세요...")
        print("(마이크 레벨이 실시간으로 표시됩니다)")
        
        start_time = time.time()
        while time.time() - start_time < 5.0:
            try:
                # 짧은 녹음으로 레벨 측정
                audio_data = audio_io.record_audio(duration=0.1)
                
                if audio_data:
                    # numpy 배열로 변환하여 레벨 계산
                    import wave
                    import io
                    
                    wav_buffer = io.BytesIO(audio_data)
                    with wave.open(wav_buffer, 'rb') as wf:
                        frames = wf.readframes(-1)
                        audio_array = np.frombuffer(frames, dtype=np.int16)
                        
                        # RMS 레벨 계산
                        if len(audio_array) > 0:
                            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                            level = min(100, int(rms / 327.67))  # 0-100 범위로 정규화
                            
                            # 레벨 바 표시
                            bar = "█" * (level // 5)
                            print(f"\r🎤 레벨: {level:3d}% |{bar:<20}|", end="", flush=True)
                        else:
                            print(f"\r🎤 레벨:   0% |{'':<20}|", end="", flush=True)
                
            except Exception as e:
                print(f"\r🎤 레벨 측정 오류: {e}", end="", flush=True)
                break
        
        print("\n✅ 마이크 레벨 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 마이크 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🔧 오디오 시스템 종합 테스트")
    print("=" * 50)
    
    # 1. 오디오 장치 확인
    if not test_audio_devices():
        print("❌ 오디오 장치 확인 실패 - 테스트 중단")
        return
    
    # 2. TTS 테스트
    if not test_simple_tts():
        print("❌ TTS 테스트 실패")
    
    # 3. 마이크 테스트
    if not test_mic_level():
        print("❌ 마이크 테스트 실패")
    
    print("\n📋 테스트 요약:")
    print("   - SPK VOLUME 50%에서 소리가 안 들렸다면 출력 장치 설정 확인")
    print("   - MIC LEVEL이 안 움직였다면 입력 장치 권한 확인")
    print("   - 전체적으로 문제가 있다면 시스템 오디오 설정 확인")

if __name__ == "__main__":
    main() 