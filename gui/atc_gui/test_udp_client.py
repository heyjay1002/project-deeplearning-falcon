"""
UDP 수신 테스트 클라이언트
- 서버에서 전송하는 프레임을 직접 수신해서 확인
"""

import socket
import cv2
import numpy as np
import time

def test_udp_receive():
    # UDP 소켓 생성
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 4100))  # 모든 인터페이스에서 4100 포트로 수신
    
    print("UDP 수신 대기 중... (포트 4100)")
    print("서버에서 CCTV 요청을 보내세요")
    print("종료: Ctrl+C 또는 OpenCV 창에서 ESC/Q 키")
    
    frame_count = 0
    
    try:
        while True:
            # 데이터 수신
            data, addr = sock.recvfrom(65536)
            frame_count += 1
            
            print(f"프레임 {frame_count} 수신: {len(data)} bytes from {addr}")
            
            # 헤더 파싱
            try:
                first_colon = data.find(b':')
                second_colon = data.find(b':', first_colon + 1)
                
                if first_colon != -1 and second_colon != -1:
                    camera_id = data[:first_colon].decode('utf-8')
                    image_id = data[first_colon + 1:second_colon].decode('utf-8')
                    frame_data = data[second_colon + 1:]
                    
                    print(f"  카메라: {camera_id}, 이미지ID: {image_id}, 데이터: {len(frame_data)} bytes")
                    
                    # 이미지 디코딩 시도
                    frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        print(f"  이미지 디코딩 성공: {frame.shape}")
                        # 화면에 표시
                        cv2.imshow(f'Camera {camera_id}', frame)
                        
                        # ESC 키나 'q' 키로 종료
                        key = cv2.waitKey(1) & 0xFF
                        if key == 27 or key == ord('q'):  # ESC 또는 'q'
                            print("키보드 입력으로 종료")
                            return
                    else:
                        print("  이미지 디코딩 실패")
                        
                else:
                    print("  헤더 파싱 실패")
                    
            except Exception as e:
                print(f"  데이터 처리 오류: {e}")
                
    except KeyboardInterrupt:
        print("\n종료...")
    finally:
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test_udp_receive()