import pyaudio
import wave
import io
import base64
import threading
import time
from typing import Optional

class AudioIO:
    def __init__(self, sample_rate=16000, chunk_size=1024, channels=1, format=pyaudio.paInt16):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.recorded_frames = []
        
    def start_recording(self):
        """
        마이크 녹음 시작 (비동기)
        """
        if self.is_recording:
            return
            
        self.is_recording = True
        self.recorded_frames = []
        
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # 별도 스레드에서 녹음
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.start()
            
        except Exception as e:
            print(f"[AudioIO] 녹음 시작 오류: {e}")
            self.is_recording = False
    
    def _record_audio(self):
        """
        실제 녹음 처리 (내부 메서드)
        """
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.recorded_frames.append(data)
            except Exception as e:
                print(f"[AudioIO] 녹음 중 오류: {e}")
                break
    
    def stop_recording(self) -> bytes:
        """
        마이크 녹음 중지 및 WAV 데이터 반환
        """
        if not self.is_recording:
            return b""
            
        self.is_recording = False
        
        # 녹음 스레드 종료 대기
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join(timeout=1.0)
        
        # 스트림 정리
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        
        # WAV 파일 생성
        if not self.recorded_frames:
            return b""
            
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.recorded_frames))
        
        wav_data = wav_buffer.getvalue()
        wav_buffer.close()
        
        return wav_data
    
    def record_audio(self, duration: float = 5.0) -> bytes:
        """
        지정된 시간 동안 마이크로부터 WAV 포맷 음성 녹음
        """
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print(f"[AudioIO] {duration}초 동안 녹음 시작...")
            frames = []
            
            for _ in range(int(self.sample_rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # WAV 파일 생성
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            wav_data = wav_buffer.getvalue()
            wav_buffer.close()
            
            print("[AudioIO] 녹음 완료")
            return wav_data
            
        except Exception as e:
            print(f"[AudioIO] 녹음 오류: {e}")
            return b""

    def play_audio(self, audio_bytes: bytes):
        """
        WAV 바이트 데이터를 스피커로 출력
        """
        try:
            # WAV 데이터 파싱
            wav_buffer = io.BytesIO(audio_bytes)
            with wave.open(wav_buffer, 'rb') as wf:
                # 오디오 스트림 열기
                stream = self.audio.open(
                    format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                print("[AudioIO] 오디오 재생 시작...")
                
                # 청크 단위로 재생
                data = wf.readframes(self.chunk_size)
                while data:
                    stream.write(data)
                    data = wf.readframes(self.chunk_size)
                
                stream.stop_stream()
                stream.close()
                
            wav_buffer.close()
            print("[AudioIO] 오디오 재생 완료")
            
        except Exception as e:
            print(f"[AudioIO] 재생 오류: {e}")
    
    def play_audio_base64(self, audio_base64: str):
        """
        base64 인코딩된 오디오 데이터를 디코딩 후 스피커 출력
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            self.play_audio(audio_bytes)
        except Exception as e:
            print(f"[AudioIO] Base64 오디오 재생 오류: {e}")
    
    def audio_to_base64(self, audio_bytes: bytes) -> str:
        """
        오디오 바이트 데이터를 base64로 인코딩
        """
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def __del__(self):
        """
        소멸자 - PyAudio 정리
        """
        if hasattr(self, 'audio'):
            self.audio.terminate()
