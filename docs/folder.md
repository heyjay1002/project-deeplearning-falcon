### 폴더 구조


### 딥러닝 기술조사
##### 조사하고자하는 기능에 대해 폴더 생성후 데이터셋을 제외한 학습 모델 및 data.yaml, 성능 지표 기입. 
##### 모델 따로 추가시 해당 기능 폴더 및에 폴더 추가 생성
```
technical_test/
├── dl_model_test/             # 딥러닝 모델 조사
│   ├── object_detecting/      # 객체감지
│   │   ├── single_model/          # 단일모델로 감지
│   │   │   ├── yolov11s_box/
│   │   │   │   ├── bird_airplane_animal_fod_human/
│   │   │   │   └── finefurning_v1/   # 클래스 3~400장 추가 학습
│   │   │   └── yolov8s_seg/
│   │   │       └── bird_airplane_animal_fod_human/
│   │   └── multi_model/
│   │       └── bird/
│   ├── pose/
│   ├── stt_tts/
│   └── 기술조사 추가 시 작성
│
│
│ # 통신 테스트 조사
├── api_server_test/ 
│   ├── camera_to_falcon_gui_tcp/   
│   └── camera_to_falcon_gui_tcp    # 테스트하는 보내는곳과 받는곳으로 폴더 생성후 쓰시면 됩니다.  
```