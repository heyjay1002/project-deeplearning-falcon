# 간단한 테스트 스크립트
from detector import Detector
from config import Settings
import cv2

settings = Settings()
detector = Detector(settings)

# 웹캠에서 한 프레임 테스트
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    result = detector.process_object_mode(frame, 12345)
    print("감지 결과:", result)
cap.release()