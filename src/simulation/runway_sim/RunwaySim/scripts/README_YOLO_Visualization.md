# YOLO 라벨 시각화 도구

RunwayRiskSim 프로젝트의 `yolo_capture` 데이터를 시각화하는 도구입니다.

## 🚀 빠른 시작

### 1. 전체 데이터셋 분석
```bash
python3 scripts/visualize_yolo_labels.py --analyze-only
```

### 2. 특정 카메라 시각화 (최신 10개 이미지)
```bash
python3 scripts/visualize_yolo_labels.py --camera Fixed_Camera_A --max-images 10
```

### 3. 모든 카메라 시각화 (각각 최대 20개 이미지)
```bash
python3 scripts/visualize_yolo_labels.py --max-images 20
```

### 4. 상세 정보와 함께 시각화
```bash
python3 scripts/visualize_yolo_labels.py --camera Fixed_Camera_A --details --max-images 5
```

## 📋 주요 기능

### ✅ 데이터셋 분석
- 전체 이미지/라벨 파일 수 통계
- 카메라별 객체 검출률
- 클래스별 분포 (Bird, Airplane 등)
- 빈 프레임 vs 객체 포함 프레임 비율

### 🎨 시각화 기능
- YOLO 바운딩 박스 그리기
- 클래스별 색상 구분 (Bird: 초록색, Airplane: 빨간색)
- 중심점 표시
- 프레임 정보 및 통계 오버레이

### 📊 리포트 생성
- JSON 형식의 상세 분석 리포트
- 타임스탬프가 포함된 파일명
- 카메라별/클래스별 세부 통계

## 🛠️ 명령어 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input, -i` | yolo_capture 디렉토리 경로 | `data/yolo_capture` |
| `--output, -o` | 출력 디렉토리 경로 | `data/yolo_visualization` |
| `--camera, -c` | 특정 카메라만 처리 | 모든 카메라 |
| `--max-images, -m` | 카메라당 최대 처리 이미지 수 | 50 |
| `--analyze-only, -a` | 분석만 수행 (시각화 안함) | False |
| `--details, -d` | 상세 정보 표시 (좌표, 크기) | False |
| `--no-save` | 이미지 저장하지 않음 | False |

## 📂 출력 구조

```
data/yolo_visualization/
├── yolo_analysis_report_YYYYMMDD_HHMMSS.json    # 분석 리포트
├── Fixed_Camera_A/                              # 카메라별 폴더
│   ├── labeled_frame_00001.png                  # 시각화된 이미지
│   ├── labeled_frame_00002.png
│   └── ...
└── Fixed_Camera_B/
    ├── labeled_frame_00001.png
    └── ...
```

## 🎯 클래스 정보

현재 지원하는 클래스:

| 클래스 ID | 클래스명 | 색상 |
|-----------|----------|------|
| 0 | Bird | 초록색 |
| 4 | Airplane | 빨간색 |

## 📈 분석 리포트 예시

```json
{
  "timestamp": "20250618_200010",
  "analysis_time": "2025-06-18T20:00:10.123456",
  "statistics": {
    "total": {
      "images": 68,
      "labels": 68,
      "objects": 240,
      "empty_frames": 0,
      "classes": {
        "Bird": 240
      }
    },
    "cameras": {
      "Fixed_Camera_A": {
        "images": 34,
        "labels": 34,
        "objects": 120,
        "empty_frames": 0,
        "classes": {
          "Bird": 120
        }
      }
    }
  }
}
```

## 🔧 문제 해결

### OpenCV 설치
```bash
pip install opencv-python
```

### 권한 오류
```bash
chmod +x scripts/visualize_yolo_labels.py
```

### Python 경로 문제
- `python3` 대신 `python` 사용해보기
- 가상환경 활성화 확인

## 💡 사용 팁

1. **대용량 데이터셋**: `--max-images` 옵션으로 처리량 제한
2. **빠른 확인**: `--analyze-only`로 분석만 먼저 실행
3. **특정 카메라**: `--camera` 옵션으로 원하는 카메라만 처리
4. **디버깅**: `--details` 옵션으로 좌표/크기 정보 확인
5. **스토리지 절약**: `--no-save`로 분석만 수행

## 📝 예시 사용 시나리오

### 시나리오 1: 새로운 데이터 검증
```bash
# 1. 전체 분석
python3 scripts/visualize_yolo_labels.py --analyze-only

# 2. 샘플 시각화
python3 scripts/visualize_yolo_labels.py --max-images 5 --details
```

### 시나리오 2: 특정 카메라 문제 진단
```bash
# 문제가 있는 카메라만 상세 분석
python3 scripts/visualize_yolo_labels.py --camera Fixed_Camera_A --details --max-images 20
```

### 시나리오 3: 프레젠테이션용 이미지 생성
```bash
# 고품질 시각화 (적은 수의 대표 이미지)
python3 scripts/visualize_yolo_labels.py --max-images 3 --details
``` 