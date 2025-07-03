import cv2
import cv2.aruco as aruco

# --- 1. 마커 딕셔너리 및 파라미터 설정 ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# --- 2. 웹캠 열기 ---
cap = cv2.VideoCapture(4)  # 0번 카메라
if not cap.isOpened():
    print("❌ 웹캠을 열 수 없습니다.")
    exit()

print("✅ ArUco 마커 인식 시작 (ID 0~3 예상)")
while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ 프레임을 읽을 수 없습니다.")
        break

    # --- 3. 마커 검출 ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detector = aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(gray)

    # --- 4. 마커 표시 및 정보 출력 ---
    if ids is not None:
        for i, id in enumerate(ids.flatten()):
            print(f"🟩 ID: {id} / 코너 좌표: {corners[i][0]}")
        frame = aruco.drawDetectedMarkers(frame, corners, ids)

    # --- 5. 화면 출력 ---
    cv2.imshow("ArUco Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC 키 종료
        break

cap.release()
cv2.destroyAllWindows()
