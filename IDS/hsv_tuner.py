# hsv_tuner.py
import cv2
import numpy as np

def nothing(x):
    pass

# 웹캠 또는 이미지 파일 경로 설정
# WEBCAM_MODE = True
WEBCAM_MODE = False
IMAGE_PATH = '/home/mac/model_test_images/train_00000 (Copy).jpg' # << 여기에 테스트할 이미지 경로를 입력하세요

# 트랙바 윈도우 생성
cv2.namedWindow('HSV Tuner')
cv2.createTrackbar('H_min', 'HSV Tuner', 0, 179, nothing)
cv2.createTrackbar('S_min', 'HSV Tuner', 0, 255, nothing)
cv2.createTrackbar('V_min', 'HSV Tuner', 0, 255, nothing)
cv2.createTrackbar('H_max', 'HSV Tuner', 179, 179, nothing)
cv2.createTrackbar('S_max', 'HSV Tuner', 255, 255, nothing)
cv2.createTrackbar('V_max', 'HSV Tuner', 255, 255, nothing)

# 초기값 설정 (config.py 값으로 시작)
cv2.setTrackbarPos('H_min', 'HSV Tuner', 20)
cv2.setTrackbarPos('S_min', 'HSV Tuner', 100)
cv2.setTrackbarPos('V_min', 'HSV Tuner', 100)
cv2.setTrackbarPos('H_max', 'HSV Tuner', 30)
cv2.setTrackbarPos('S_max', 'HSV Tuner', 255)
cv2.setTrackbarPos('V_max', 'HSV Tuner', 255)

if WEBCAM_MODE:
    cap = cv2.VideoCapture(0)
else:
    frame = cv2.imread(IMAGE_PATH)
    if frame is None:
        print(f"이미지를 불러올 수 없습니다: {IMAGE_PATH}")
        exit()

while True:
    if WEBCAM_MODE:
        ret, frame = cap.read()
        if not ret:
            break

    # HSV 변환
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 트랙바에서 현재 값 가져오기
    h_min = cv2.getTrackbarPos('H_min', 'HSV Tuner')
    s_min = cv2.getTrackbarPos('S_min', 'HSV Tuner')
    v_min = cv2.getTrackbarPos('V_min', 'HSV Tuner')
    h_max = cv2.getTrackbarPos('H_max', 'HSV Tuner')
    s_max = cv2.getTrackbarPos('S_max', 'HSV Tuner')
    v_max = cv2.getTrackbarPos('V_max', 'HSV Tuner')

    # HSV 범위 설정
    lower_bound = np.array([h_min, s_min, v_min])
    upper_bound = np.array([h_max, s_max, v_max])

    # 마스크 생성 및 결과 보기
    mask = cv2.inRange(hsv, lower_bound, upper_bound)
    result = cv2.bitwise_and(frame, frame, mask=mask)

    # 결과 출력
    cv2.imshow('Original', frame)
    cv2.imshow('Mask', mask)
    cv2.imshow('Result', result)

    print(f"LOWER: ({h_min}, {s_min}, {v_min})  UPPER: ({h_max}, {s_max}, {v_max})")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if WEBCAM_MODE:
    cap.release()
cv2.destroyAllWindows()