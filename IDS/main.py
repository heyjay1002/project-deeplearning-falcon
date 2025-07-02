# main.py

from multiprocessing import Process, Queue
# [수정] threading.Thread 임포트가 더 이상 필요하지 않습니다.
import time
from config import Settings
from camera import CameraWorker
from inference import InferenceWorker
from communicator import TcpCommunicator # TcpCommunicator 클래스를 직접 사용합니다.

def main():
    settings = Settings()

    # 1. 큐 정의
    inference_queue = Queue(maxsize=settings.INFERENCE_QUEUE_SIZE)
    tcp_queue = Queue(maxsize=settings.TCP_EVENT_QUEUE_SIZE)
    mode_queue = Queue(maxsize=1)

    # 2. 워커/통신기 생성
    processes = [
        Process(
            target=CameraWorker,
            args=(inference_queue, settings),
            name="CameraProcess"
        ),
        Process(
            target=InferenceWorker,
            args=(inference_queue, tcp_queue, mode_queue, settings),
            name="InferenceProcess"
        )
    ]
    
    # [수정] TcpCommunicator 클래스의 인스턴스를 직접 생성합니다.
    # daemon=True는 TcpCommunicator의 __init__에서 이미 설정되어 있습니다.
    tcp_thread = TcpCommunicator(
        tcp_queue, 
        mode_queue, 
        settings
    )
    # 인스턴스의 이름을 설정할 수도 있습니다.
    tcp_thread.name = "TcpThread"

    try:
        # 3. 실행
        for p in processes:
            p.start()
        tcp_thread.start() # 인스턴스의 start() 메소드를 호출

        # 4. 종료 대기
        for p in processes:
            p.join()

    except KeyboardInterrupt:
        print("\n🛑 [종료 시작] 시스템을 종료합니다...")
    finally:
        for p in processes:
            if p.is_alive():
                print(f"Terminating process: {p.name}")
                p.terminate()
                p.join()
        print("✅ 모든 프로세스가 성공적으로 종료되었습니다.")


if __name__ == "__main__":
    main()