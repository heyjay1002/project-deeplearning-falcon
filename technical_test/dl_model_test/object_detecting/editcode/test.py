from ultralytics import YOLO

# 1. 모델 불러오기 (너가 파인튜닝한 best.pt 경로)
model = YOLO("/home/mac/dev_ws/project/deeplearning-repo-2/technical_test/dl_model_test/object_detecting/single_model/yolo8s_seg/all_fine_fune_v1/weights/best.pt")

# 2. 테스트할 대상 경로
# - 이미지: JPG/PNG
# - 폴더: 폴더 경로
# - 웹캠: 0
# - 영상: MP4 경로
source = "/home/mac/Videos/Screencasts/Screencast from 2025-06-03 16-31-44.webm"  # 웹캠이면 0 / 이미지 경로면 "C:/경로/파일.jpg"

# 3. 추론 실행
results = model.predict(
    source=source,
    imgsz=2560,
    conf=0.2,
    show=True,       # 화면에 바로 표시
    save=True        # runs/segment/predict에 저장
)

# 4. 결과 확인
for r in results:
    print("Saved to:", r.save_dir)
