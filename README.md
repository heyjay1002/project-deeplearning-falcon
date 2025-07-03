![Banner](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/banner.png?raw=true)

# FALCON: 딥러닝 기반 항공 운항 안전 서비스
> Foreign object Auto-detection & Localization Camera Observation Network

[발표자료 보기](https://docs.google.com/presentation/d/1z73na_gwi2OX0oAGJ8FHGI7qYufhDPk5QCgtm7bIQoM/edit?usp=sharing)

---

# 📚 목차

1. A
2. B
3. C
4. D
5. E
6. F

---

# 🧭 프로젝트 개요

## 🚨 추진 배경

실제 공항에서는 다음과 같은 중대 사고들이 반복적으로 발생하고 있음:

- **무안공항 제주항공 조류충돌 사고 (2024)**  
  - 접근 중 가창오리 떼와 충돌  
  - Go-around 후 랜딩기어 미전개 상태로 동체 착륙  
  - 활주로 이탈 및 기체 화재 → 탑승자 181명 중 179명 사망  
  - 📌 *전방위 조류 감지 시스템 부재*

- **콩코드 여객기 FOD 충돌 사고 (2000)**  
  - 활주로 금속 이물질(FOD)과 접촉 → 타이어 파열 → 연료탱크 손상  
  - 이륙 직후 기체 화재 → 인근 호텔에 충돌, 총 113명 사망  
  - 📌 *FOD 제거 실패, 활주로 점검 미흡*

- **오스틴 공항 활주로 오진입 사고 (2023)**  
  - 짙은 안개 속 이착륙 항공기 간 거리 46m로 충돌 직전 회피  
  - 관제사의 이륙 허가 및 감시 시스템 부재로 인한 오판  
  - 📌 *관제 시스템 부재 + 판단 오류 복합 문제*
 
---

## ⚠️ 기존 시스템의 한계

<p align="center">
  <img src="https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/background_1.png?raw=true" width="90%">
</p>

| **탐지 한계** | **판단 한계** |
|---------------|----------------|
| 관제사의 **육안 감시** 의존 → 시야각, 기상, 거리 제약 발생 | 관제사의 **인지 부하** → 다수 객체(항공기, 차량, 조류 등) 동시 판단 필요 |
| **조류 레이더**의 탐지 정확도 및 범위 제한 → 일부 공항만 도입 | 조종사의 **인지 부하** → 유도사 수신호, 관제 지시, 주변 위험 동시 인지 필요 |

---

## 💡 FALCON의 핵심 가치

<p align="center">
  <img src="https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/value.png?raw=true" width="90%">
</p>

- **위험요소 탐지 자동화**  
  사람이 놓치는 위험요소를 실시간으로 감지하여 사각지대를 해소

- **판단 보조**  
  수신호 해석, 위험 판단, 음성 질의응답 등을 통해 인지 부담을 경감

- **정보 전달 최적화**  
  위험 정보를 GUI 또는 TTS로 자동 전달하여 반응 속도를 향상

---

# 🔧 주요 기능

FALCON은 관제사와 조종사를 위한 AI 서비스를 통해 공항 내 다양한 위험요소에 능동적으로 대응하는 기능을 제공한다.

<p align="center">
  <img src="https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/core_features.png?raw=true" width="90%">
</p>


---

### 🛫 관제사 AI 서비스: **Hawkeye**
> 지상에서 발생하는 다양한 위험요소를 실시간으로 감지하고, GUI를 통해 시각적 피드백 및 출입 통제를 자동화함으로써 관제 업무를 보조한다.

<p align="center">
  <img src="https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/hawkeye_features.png?raw=true" width="90%">
</p>

- **지상 위험요소 탐지**
  - CCTV 기반 영상 분석
  - 조류, FOD, 사람, 차량 등 탐지 시 GUI 팝업 및 지도 마커 표시
  - 위험도 상태 갱신 및 로그 생성

- **지상 쓰러짐 감지**
  - 일반인 / 작업자의 쓰러짐 상태 인식
  - 위험도 게이지 시각화 (예: 쓰러진 위치, 시간, 위험 수치)
  - 구조 필요성 판단을 위한 시각적 정보 제공

- **지상 출입 통제**
  - 구역별 출입등급 설정 (1~3단계)
  - 출입 위반 시 자동 감지 및 알림
  - 출입 조건 변경 시 실시간 GUI 반영

---

### ✈️ 조종사 AI 서비스: **RedWing**
> 조종사의 인지 부담을 줄이고, 지상 유도 및 위험 판단을 자동화하여 더 안전한 운항 결정을 돕는 인터페이스를 제공한다.

<p align="center">
  <img src="https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/redwing_features.png?raw=true" width="90%">
</p>

- **운항 위험 경보**
  - 조류 충돌, 활주로 위험요소 등을 실시간 TTS로 경고
  - 영상 분석 + 위험 판단 모델 연동

- **위험도 질의 자동응답**
  - 음성 질의(STT) → LLM 분류 → 음성 응답(TTS)
  - 예: “Runway Alpha status?” → “Runway Alpha is CLEAR.”
  - [영상 보기](https://youtu.be/VvQjRLMTrvU)

- **지상 유도 보조**
  - CCTV 영상 내 유도사 수신호(정지, 전진, 좌우회전 등) 인식
  - 수신호 분석 결과를 조종사에게 음성 안내로 전달
  - [영상 보기](https://youtu.be/sB_zEFfP7kI)
---

## 🧠 핵심 기술

> FALCON은 딥러닝 기반 객체 인식, 포즈 분석, 추적, 좌표 변환, 시뮬레이션 등 다양한 기술 요소들을 통합하여 공항 지상 안전을 실시간으로 관리한다.

---

### 1) 객체 탐지 (Object Detection)

- **탐지 대상 클래스**:  
  `조류`, `FOD`, `사람`, `야생동물`, `항공기`, `차량` (총 6종)

- **모델 및 학습 전략**:
  - `YOLOv8-seg` 및 `YOLOv8-box` 기반 모델 학습
  - 실제 촬영 + 합성 이미지 결합한 **Hybrid Dataset** 사용
  - **Polycam + Blender + Unity** 활용한 자동 라벨링 파이프라인 구축
    - 1시간당 약 3,000장 생성 가능
    - 다양한 조명, 각도, 환경조건 시뮬레이션 가능

- **후처리 식별 기술**:
  - OpenCV를 활용해 탐지된 사람의 **형광 조끼** 착용 여부 분석
  - 차량 색상을 기반으로 **작업차량 여부** 재분류

---

### 2) 객체 추적 (Object Tracking)

- **지상 객체 추적**:
  - `ByteTrack` 알고리즘 사용 (Ultralytics 내장)
  - `Low Score Detection` + `Kalman Filter` 기반 예측
  - 실시간성과 정확성 우수

- **공중 객체 추적 (조류)**:
  - **삼각측량 + ByteTrack** 결합
  - 두 대의 CCTV 동기화 프레임 기반 2D 좌표 → 3D 공간 좌표 변환
  - 조류 속도 및 위치를 기반으로 **실시간 충돌 위험도 계산**

---

### 3) 자세 감지 (Pose Estimation)

- **정적 자세 감지**:
  - `YOLOv8n-pose` 사용
  - Blender로 생성한 합성 포즈 데이터셋(683장) + 실제 촬영 이미지 학습
  - 쓰러짐 상태를 **Keypoint 기울기 분석**으로 판단

- **동적 자세 감지**:
  - **TCN (Temporal Convolutional Network)** 기반 시계열 분류
  - `MediaPipe`로 17개 관절 좌표 추출 → 어깨 기준 정규화 → 30프레임 시퀀스로 구성
  - ICAO 표준 유도 제스처(정지, 전진, 좌/우회전) 인식

---

### 4) 좌표계 변환 (Coordinate Mapping)

- **ArUco 기반 실제 맵 좌표 변환**:
  - OpenCV의 `perspectiveTransform()` 사용
  - ArUco 마커 중심점의 픽셀 좌표 ↔ 실제 좌표로 매핑
  - 오차 범위 ±5mm/픽셀 수준의 정밀도

- **객체 중심 좌표 보정**:
  - 감지된 객체의 Bounding Box 중심을 실시간 위치로 변환
  - 구역 침범 여부, 출입 위반 판단 등에 활용

---

### 5) 시뮬레이션 기반 위험 예측

- **Unity 기반 공항 환경 시뮬레이터 구성**:
  - 실제 활주로 및 주변 환경 모델링
  - 조류 이동 경로, 항공기 이륙/착륙 경로 시나리오 생성

- **실시간 위험도 시뮬레이션**:
  - CCTV 영상 기반 조류 위치 예측
  - 항공기와의 상대 거리, 속도를 분석하여 **충돌 확률 수치화**

---

## 🧪 기술적 문제 및 해결

### 📉 YOLO 정확도 저하
- 문제: 실사 기반 테스트 시 객체 탐지 정확도 낮음
- 해결:
  - Polycam + Blender + Unity로 합성 데이터셋 생성
  - 자동 라벨링 파이프라인 구축 (1시간 3000장 생성)
  - 실제 + 합성 데이터 결합 → Hybrid Dataset 구성

### 🧍‍♂️ Pose Keypoint 인식 오류
- 문제: 사람 모형이 눕거나 뒤집힌 상태에서 keypoint 인식률 저하
- 해결:
  - Blender로 포즈 합성 이미지 683장 생성
  - YOLOv8n-pose 모델 학습
  - 쓰러짐 감지 성능 향상 확인

---

# 시스템 설계

## 시스템 아키텍처
![system_architecture](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/software_architecture.png?raw=true)

## ER 다이어그램
![er_diagram](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/er_diagram.png?raw=true)

---

## 폴더 구조 요약

```
FALCON/
├── src/
│   ├── systems/              # 핵심 시스템
│   │   ├── bds/             # Bird Detection System
│   │   └── ids/             # Intrusion Detection System
│   │
│   ├── simulation/          # 시뮬레이션
│   │   ├── bird_sim/        # 새 충돌 시뮬레이션
│   │   └── runway_sim/      # 활주로 시뮬레이션
│   │
│   ├── interfaces/          # 사용자 인터페이스
│   │   ├── hawkeye/         # 관제사용 GUI
│   │   └── redwing/         # 조종사용 GUI
│   │
│   ├── infrastructure/      # 시스템 인프라
│   │   ├── server/          # 서버 코드
│   │   ├── network/         # 네트워크 통신
│   │   └── database/        # 데이터베이스
│   │
│   ├── shared/              # 공통 모듈
│   │   ├── utils/           # 유틸리티
│   │   ├── models/          # AI 모델
│   │   └── protocols/       # 통신 프로토콜
│   │
│   └── tests/               # 테스트 코드
│       └── technical_test/  # 기술 검증
│
├── docs/                    # 문서
├── assets/                  # 리소스
├── tools/                   # 도구
└── README.md               # 프로젝트 설명서
```

---

## 🛠️ 기술 스택

| 분류 | 사용 기술 |
|------|-----------|
| **ML / DL** | ![YOLOv8](https://img.shields.io/badge/YOLOv8-FFB400?style=for-the-badge&logo=yolov5&logoColor=black) ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white) ![ByteTrack](https://img.shields.io/badge/ByteTrack-222222?style=for-the-badge&logo=github&logoColor=white) ![TCN](https://img.shields.io/badge/TCN-800080?style=for-the-badge&logo=neural&logoColor=white) ![MediaPipe](https://img.shields.io/badge/MediaPipe-FF6F00?style=for-the-badge&logo=google&logoColor=white)<br>![Whisper](https://img.shields.io/badge/Whisper-9467BD?style=for-the-badge&logo=openai&logoColor=white) ![Ollama](https://img.shields.io/badge/Ollama-333333?style=for-the-badge&logo=vercel&logoColor=white) ![Coqui](https://img.shields.io/badge/Coqui-FFD166?style=for-the-badge&logo=soundcloud&logoColor=black) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white) ![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white) |
| **GUI** | ![PyQt6](https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white) |
| **데이터베이스** | ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white) |
| **네트워크 / 통신** | ![Socket](https://img.shields.io/badge/Socket-000000?style=for-the-badge&logo=socketdotio&logoColor=white) ![JSON](https://img.shields.io/badge/JSON-292929?style=for-the-badge&logo=json&logoColor=white) ![UDP](https://img.shields.io/badge/UDP-D8B4FE?style=for-the-badge&logo=wifi&logoColor=white) ![TCP](https://img.shields.io/badge/TCP-004E64?style=for-the-badge&logo=networkx&logoColor=white) |
| **분석 / 시각화** | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white) ![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=chartdotjs&logoColor=white) |
| **시뮬레이션 / 합성 데이터** | ![Unity](https://img.shields.io/badge/Unity-000000?style=for-the-badge&logo=unity&logoColor=white) ![Blender](https://img.shields.io/badge/Blender-F5792A?style=for-the-badge&logo=blender&logoColor=white) ![Polycam](https://img.shields.io/badge/Polycam-272727?style=for-the-badge&logo=camera&logoColor=white) |



---

## 👥 팀 구성

### 🧑‍💼 김종명 [`@jongbob1918`](https://github.com/jongbob1918)
- 프로젝트 총괄  
- 프로젝트 문서 관리  
- 지상 감지 AI 서버 구축  
- 지상 객체 탐지를 위한 딥러닝 모델 기술조사 및 제작

### 🧑‍💼 김지연 [`@heyjay1002`](https://github.com/heyjay1002)
- Blender 이용 Pose Keypoint 추출 및 합성 데이터셋 생성  
- 쓰러짐 기반 YOLO Pose Custom Model 제작  
- LLM 및 음성 처리 기능(STT/TTS) 기술조사  
- 관제사 GUI 설계 및 기능 구현

### 🧑‍💼 박효진 [`@Park-hyojin`](https://github.com/Park-hyojin)
- 시스템 설계 총괄  
- 메인 서버 구축 및 관리  
- 데이터베이스 구축 및 관리  
- 시스템 인터페이스 및 통신 구조 설계  
- 아루코 마커 기반 맵 좌표 변환 로직 설계

### 🧑‍💼 장진혁 [`@jinhyuk2me`](https://github.com/jinhyuk2me)
- Unity 시뮬레이션 기반 합성 데이터 파이프라인 구현  
- 실시간 조류 충돌 분석 시스템 설계 및 구현  
- 지상 객체 및 조류 탐지를 위한 딥러닝 모델 제작  
- 조종사 음성 인터페이스 및 LLM 연동 기능 구현  
- 파일럿 AI 서비스 전체 기능 설계 및 구현

---

## 📋 일정 관리


