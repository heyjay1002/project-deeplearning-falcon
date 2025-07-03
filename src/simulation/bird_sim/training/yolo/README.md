# BirdRiskSim YOLOv8s 학습 가이드

새떼-비행기 탐지를 위한 YOLOv8s 모델 학습 및 사용 가이드입니다.

## 📋 목차
- [환경 설정](#환경-설정)
- [데이터 준비](#데이터-준비)
- [학습 실행](#학습-실행)
- [모델 평가](#모델-평가)
- [추론 실행](#추론-실행)
- [폴더 구조](#폴더-구조)

## 🔧 환경 설정

### 1. 필수 패키지 설치
```bash
# YOLOv8 및 관련 패키지 설치
pip install -r requirements.txt
```

### 2. GPU 환경 확인 (권장)
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## 📊 데이터 준비

### 1. 데이터셋 구조 생성 및 분할
```bash
# 데이터 준비 스크립트 실행
python setup_training.py
```

이 스크립트는 다음 작업을 수행합니다:
- `../../data/yolo_capture`에서 이미지와 라벨 수집
- 80% 훈련용, 20% 검증용으로 분할
- YOLO 형식의 디렉토리 구조 생성:
  ```
  training/yolo/
  ├── dataset/             # 학습 데이터
  │   ├── images/         # 이미지 파일
  │   │   ├── train/     # 학습용 이미지
  │   │   └── val/       # 검증용 이미지
  │   └── labels/        # 라벨 파일
  │       ├── train/     # 학습용 라벨
  │       └── val/       # 검증용 라벨
  └── dataset.yaml
  ```

### 2. 클래스 정보
- **클래스 0**: Flock (새떼) 🐦
- **클래스 1**: Airplane (비행기) ✈️

## 🚀 학습 실행

### 기본 학습 (YOLOv8s 사용)
```bash
python train.py
```

### 커스텀 설정으로 학습
```bash
# 에포크 수 변경
python train.py --epochs 200

# 배치 크기 지정
python train.py --batch 16

# 다른 모델 크기 사용
python train.py --model yolov8m

# 체크포인트에서 재시작
python train.py --resume runs/train/bird_detection_YYYYMMDD_HHMMSS/weights/last.pt
```

### 학습 파라미터
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `--model` | `yolov8s` | 모델 크기 (n/s/m/l/x) |
| `--epochs` | `100` | 학습 에포크 수 |
| `--batch` | `-1` | 배치 크기 (-1은 자동) |
| `--imgsz` | `640` | 이미지 크기 |

## 📊 모델 평가

### 종합 평가 실행
```bash
python evaluate.py
```

### 커스텀 평가
```bash
# 특정 모델 평가
python evaluate.py --model weights/best_bird_detection.pt

# 신뢰도 임계값 변경
python evaluate.py --conf 0.5

# 공식 검증 건너뛰기
python evaluate.py --skip-official
```

### 평가 결과
평가 완료 후 `training/results/evaluation/` 폴더에 다음 파일들이 생성됩니다:
- `class_distribution.png`: 클래스 분포 비교 그래프
- `confidence_analysis.png`: 신뢰도별 성능 분석

## 🔍 추론 실행

### 단일 이미지 추론
```bash
python inference.py --source path/to/image.png
```

### 폴더 일괄 추론
```bash
python inference.py --source path/to/image/folder
```

### 추론 설정
```bash
# 신뢰도 임계값 변경
python inference.py --source image.png --conf 0.5

# 특정 모델 사용
python inference.py --source image.png --model weights/custom_model.pt

# 최대 처리 이미지 수 제한
python inference.py --source folder/ --max-images 50
```

### 추론 결과
- 결과 이미지는 `training/results/detections/` 폴더에 저장됩니다
- 탐지된 객체에 바운딩 박스와 신뢰도가 표시됩니다
- **Flock**: 초록색 박스 🟢
- **Airplane**: 빨간색 박스 🔴

## 📁 폴더 구조
```
model/yolo/
├── setup_training.py      # 데이터 준비 스크립트
├── train.py              # 학습 스크립트
├── inference.py          # 추론 스크립트
├── evaluate.py           # 평가 스크립트
├── requirements.txt      # 필수 패키지 목록
├── README.md            # 이 파일
│
├── dataset/             # 학습 데이터 (setup_training.py 실행 후 생성)
│   ├── images/
│   ├── labels/
│   └── dataset.yaml
│
├── runs/                # 학습 결과
│   └── train/
│       └── bird_detection_*/
│
├── weights/             # 저장된 모델
│   └── best_bird_detection.pt
│
├── training/
│   ├── results/          # 결과 저장 디렉토리
│   │   ├── detections/   # 추론 결과 이미지
│   │   └── evaluation/   # 평가 결과 그래프
│   └── yolo/
│
└── training/
```

## 🔄 전체 워크플로우

### 1단계: 환경 준비
```bash
pip install -r requirements.txt
```

### 2단계: 데이터 준비
```bash
python setup_training.py
```

### 3단계: 모델 학습
```bash
python train.py
```

### 4단계: 모델 평가
```bash
python evaluate.py
```

### 5단계: 추론 테스트
```bash
python inference.py --source ../../data/yolo_capture/Camera_A/frame_01200.png
```

## 📈 학습 모니터링

### TensorBoard 실행
```bash
tensorboard --logdir runs/train
```
웹 브라우저에서 `http://localhost:6006` 접속

### 주요 메트릭
- **mAP@0.5**: IoU 0.5에서의 평균 정밀도
- **mAP@0.5:0.95**: IoU 0.5-0.95에서의 평균 정밀도
- **Precision**: 정밀도
- **Recall**: 재현율
- **Loss**: 손실 함수 값

## 🛠️ 트러블슈팅

### GPU 메모리 부족 시
```bash
# 배치 크기 줄이기
python train.py --batch 8

# 이미지 크기 줄이기
python train.py --imgsz 416
```

### 학습이 수렴하지 않을 때
- 학습률 조정: `train.py`의 `lr0` 파라미터 수정
- 에포크 수 증가: `--epochs 200`
- 데이터 증강 확인: YOLO 자동 증강 활용

### 모델 성능이 낮을 때
1. 더 많은 데이터 수집
2. 라벨링 품질 확인
3. 더 큰 모델 사용 (`yolov8m` 또는 `yolov8l`)
4. 하이퍼파라미터 튜닝

## 📞 문의 및 지원
- 학습 관련 문제는 GitHub Issues에 등록해주세요
- YOLO 공식 문서: https://docs.ultralytics.com/ 