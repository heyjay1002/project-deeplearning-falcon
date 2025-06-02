### 폴더 구조


### 딥러닝 기술조사
##### 조사하고자하는 기능에 대해 폴더 생성후 데이터셋을 제외한 학습 모델 및 data.yaml, 성능 지표 기입. 
##### 모델 따로 추가시 해당 기능 폴더 및에 폴더 추가 생성
📁technical_test        # 기술조사  
ㄴ 📁 dl_model_test           # 딥러닝 모델 조사  
    ㄴ 📁 object_detecting     # 객체감지  
         ㄴ 📁 single_model      # 단일모델로 감지  
            ㄴ 📁 yolov11s_box
                ㄴ 📁 bird_airplane_animal_fod_human  
                ㄴ 📁 finefurning_v1       # 위의 모델 개선 버전1(클래스 3~400장추가로 학습)  
            ㄴ 📁 yolov8s_seg  
                ㄴ 📁 bird_airplane_animal_fod_human          
         ㄴ 📁 multi_model      # 클래스가 한두개인 모델 여러개로 감지  
            ㄴ 📁 bird  
  
    ㄴ 📁 pose  
    ㄴ 📁 stt/tts  
    ㄴ 📁 기술조사 추가 시 작성  
  
  
### 통신 기술조사  
ㄴ📁 api_server_test  
    ㄴ 📁 camera_to_falcon_gui     # 테스트하는 보내는곳과 받는곳으로 폴더 생성후 쓰시면 됩니다.  
    ㄴ 📁 camera_to_pilot_gui  
    ㄴ 📁   
  