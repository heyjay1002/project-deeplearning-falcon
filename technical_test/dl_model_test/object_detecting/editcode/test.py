from ultralytics import YOLO

# 1. 모델 불러오기 (너가 파인튜닝한 best.pt 경로)
model = YOLO("/home/mac/dev_ws/project/deeplearning-repo-2/IDS/models/yolov11seg-m_v2.pt")

# 2. 테스트할 대상 경로
# - 이미지: JPG/PNG
# - 폴더: 폴더 경로
# - 웹캠: 0
# - 영상: MP4 경로
source = "/home/mac/Downloads/model_test_iphone_2.MOV"  # 웹캠이면 0 / 이미지 경로면 "C:/경로/파일.jpg"


# 3. 추론 실행
results = model.predict(
    source=source,
    imgsz=960,
    conf=0.1,
    show=True,       # 화면에 바로 표시
    save=True        # runs/segment/predict에 저장
)

# 4. 결과 확인
for r in results:
    print("Saved to:", r.save_dir)
