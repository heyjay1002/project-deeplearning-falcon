import cv2
from ultralytics import YOLO
def main():
    cap = cv2.VideoCapture(4, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # MJPG는 필수
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
    # yolo 새 전용 모델 ("/home/mac/dev_ws/project/runs/bird_only/stage24/weights/best.pt")
    # 활주로내 물체 1차 학습모델("/home/mac/dev_ws/project/runs/FOhD-multiclass/stage29/weights/best.pt")
    # model = YOLO("/home/mac/dev_ws/project/runs/FOD-multiclass/stage29/weights/best.pt")qq
    model = YOLO("/home/mac/dev_ws/project/deeplearning-repo-2/IDS/v2/models/yolov8n_box_v0.1.0.pt")
    cv2.namedWindow("ABKO 1944p", cv2.WINDOW_NORMAL)  # 창 리사이징 가능하게 설정
    while True:
        ok, frame = cap.read()
        if not ok:
            print("💥 프레임 수신 실패"); break
        print("📷 실제 해상도:",
              cap.get(cv2.CAP_PROP_FRAME_WIDTH),
              "x",
              cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        result = model(frame)[0]
        plotted = result.plot()
        resized = cv2.resize(plotted, (1920, 1080))  # 화면 출력용 축소
        cv2.imshow("ABKO 1944p", resized)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
if __name__ == "__main__":
    main()
