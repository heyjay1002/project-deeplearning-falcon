![Banner](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/banner.png?raw=true)

# FALCON: 딥러닝 기반 항공 운항 안전 서비스
> Foreign object Auto-detection & Localization Camera Observation Network

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

| **탐지 한계** | **판단 한계** |
|---------------|----------------|
| 관제사의 **육안 감시** 의존 → 시야각, 기상, 거리 제약 발생 | 관제사의 **인지 부하** → 다수 객체(항공기, 차량, 조류 등) 동시 판단 필요 |
| **조류 레이더**의 탐지 정확도 및 범위 제한 → 일부 공항만 도입 | 조종사의 **인지 부하** → 유도사 수신호, 관제 지시, 주변 위험 동시 인지 필요 |

---

## 🎯 FALCON의 목표

FALCON 프로젝트는 공항 내에서 발생 가능한 다양한 **지상·공중 위험요소를 실시간으로 탐지**하고, 그 의미를 분석하여 **판단을 보조**하며,  
시각적 또는 음성적 방식으로 **정보 전달을 자동화**함으로써 관제사와 조종사의 인지 부하를 줄이고 **운항 안전성을 극대화**하는 것을 궁극적인 목표로 한다.

이러한 목표 달성을 위해, FALCON은 다음과 같은 기술적 흐름으로 구성된다:

1. **데이터 확보 및 증강**: 실사 기반 영상 및 3D 시뮬레이션 환경을 활용한 대규모 하이브리드 데이터셋 구축  
2. **위험요소 인식**: 객체 탐지, 추적, 포즈 분석, 쓰러짐 판단 등 다양한 위험 상황 인식  
3. **정확한 위치 해석**: ArUco 기반 좌표계 변환 및 CCTV 간 삼각측량을 통한 정밀 위치 매핑  
4. **판단 보조 시스템**: TCN, LLM 기반의 수신호 및 위험 질의 해석  
5. **정보 전달 최적화**: GUI 시각화, TTS 음성 출력 등으로 빠르고 정확한 대응 유도

---

## 💡 FALCON의 핵심 가치

- **위험요소 탐지 자동화**  
  사람이 놓치는 위험요소를 실시간으로 감지하여 사각지대를 해소

- **판단 보조**  
  수신호 해석, 위험 판단, 음성 질의응답 등을 통해 인지 부담을 경감

- **정보 전달 최적화**  
  위험 정보를 GUI 또는 TTS로 자동 전달하여 반응 속도를 향상

---

# 🔧 주요 기능

FALCON은 관제사와 조종사를 위한 AI 서비스를 통해 공항 내 다양한 위험요소에 능동적으로 대응하는 기능을 제공한다.

![core_features](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/core_features.png?raw=true)

---

### 🛫 관제사 AI 서비스: **Hawkeye**
> 지상에서 발생하는 다양한 위험요소를 실시간으로 감지하고, GUI를 통해 시각적 피드백 및 출입 통제를 자동화함으로써 관제 업무를 보조한다.

![hawkeye_features](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/hawkeye_features.png?raw=true)

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

![redwing_features](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/redwing_features.png?raw=true)

- **운항 위험 경보**
  - 조류 충돌, 활주로 위험요소 등을 실시간 TTS로 경고
  - 영상 분석 + 위험 판단 모델 연동

- **위험도 질의 자동응답**
  - 음성 질의(STT) → LLM 분류 → 음성 응답(TTS)
  - 예: “Runway Alpha status?” → “Runway Alpha is CLEAR.”
 
[▶️ request_demo.mp4 재생](https://raw.githubusercontent.com/addinedu-ros-9th/deeplearning-repo-2/main/assets/videos/request_demo.mp4)

- **지상 유도 보조**
  - CCTV 영상 내 유도사 수신호(정지, 전진, 좌우회전 등) 인식
  - 수신호 분석 결과를 조종사에게 음성 안내로 전달

[▶️ marshal_demo.mp4 재생](https://raw.githubusercontent.com/addinedu-ros-9th/deeplearning-repo-2/main/assets/videos/marshal_demo.mp4)


---

# 🔧 핵심 기술

### 1. 객체 탐지
- hello

### 2. 객체 추적
- hello

### 3. 자세 감지
- hello

### 4. 좌표계 변환
- hello

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
