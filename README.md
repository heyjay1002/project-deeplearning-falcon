![Banner](https://github.com/addinedu-ros-9th/deeplearning-repo-2/blob/main/assets/images/Banner.png?raw=true)

# FALCON: 딥러닝 기반 항공 운항 안전 서비스
> Foreign object Auto-detection & Localization Camera Observation Network

---

## 📚 목차

1. A
2. B
3. C
4. D
5. E
6. F

---

## 🛠️ 기술 스택

### ML / DL
![YOLOv8](https://img.shields.io/badge/YOLOv8-FFB400?style=for-the-badge&logo=yolov5&logoColor=black)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![ByteTrack](https://img.shields.io/badge/ByteTrack-222222?style=for-the-badge&logo=github&logoColor=white)
![TCN](https://img.shields.io/badge/TCN-005571?style=for-the-badge&logo=neural&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-FF6F00?style=for-the-badge&logo=google&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-9467BD?style=for-the-badge&logo=openai&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-333333?style=for-the-badge&logo=vercel&logoColor=white)
![Coqui](https://img.shields.io/badge/Coqui-FFD166?style=for-the-badge&logo=soundcloud&logoColor=black)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)


### GUI
![PyQt6](https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)



### 데이터베이스
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)


### 네트워크 / 통신
![Socket](https://img.shields.io/badge/Socket-000000?style=for-the-badge&logo=socketdotio&logoColor=white)
![JSON](https://img.shields.io/badge/JSON-292929?style=for-the-badge&logo=json&logoColor=white)
![UDP](https://img.shields.io/badge/UDP-005571?style=for-the-badge&logo=wifi&logoColor=white)
![TCP](https://img.shields.io/badge/TCP-004E89?style=for-the-badge&logo=networkx&logoColor=white)



### 분석 / 시각화
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=chartdotjs&logoColor=white)



### 시뮬레이션 / 합성 데이터
![Unity](https://img.shields.io/badge/Unity-000000?style=for-the-badge&logo=unity&logoColor=white)
![Blender](https://img.shields.io/badge/Blender-F5792A?style=for-the-badge&logo=blender&logoColor=white)
![Polycam](https://img.shields.io/badge/Polycam-272727?style=for-the-badge&logo=camera&logoColor=white)



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

## 🔧 핵심 기술

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
