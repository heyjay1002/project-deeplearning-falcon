@startuml
title SC_00. System 연결 시나리오 

participant "ATC GUI"     as GUI
participant "Main Server"  as Main
participant "Image Detecting Server"     as IDS

activate Main
GUI -> Main: 연결 시도 (Port)
activate GUI
GUI --> Main: 연결 성공
GUI -> GUI: 서버 상태 업데이트\n(disconnect -> connect_uncalibrate)
deactivate GUI

IDS -> Main: 연결 시도 (Port)
activate IDS
IDS --> Main: 연결 성공
IDS -> IDS: 감지 모드 변경 (Stop -> Map)
IDS -> IDS: 이미지 프레임 수신
IDS -> IDS: ArUco 마커 4개 감지 및 다각형 생성
IDS -> IDS: 보정 파라미터 생성
IDS ->> Main: 보정 파라미터 전송 (evt)\n{"type": "map_calibration", ...}
deactivate IDS

Main -> Main: 보정 파라미터 저장
Main -> IDS: 객체 탐지 요청 (cmd)\n[set_mode_object]
activate IDS
IDS -> IDS: 감지 모드 변경 (Map -> Object)
IDS --> Main: 성공 응답 (res)\n[set_mode_object, ok]
deactivate IDS

Main ->> GUI: 보정 완료 알림 (evt)\n[map_calibration_ok]
activate GUI
GUI -> GUI: 서버 상태 업데이트\n(connect_uncalibrate -> connect_calibrate)
deactivate GUI

deactivate Main

@enduml

---

@startuml
title SC_01. 위험요소 FOD 감지

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "DB Manager" as DB
participant "ATC GUI" as GUI
participant "Pilot GUI" as PM

-> IDS
activate IDS
IDS -> IDS : 이미지 프레임 수신
activate IDS
deactivate IDS
IDS ->> Main : 이미지 전송\n {카메라 ID, 이미지 ID, 이미지}
activate Main
Main -> Main : 이미지 버퍼에 저장  
activate Main
deactivate Main
IDS -> IDS : 이미지 분석\n(FOD 감지)
activate IDS
deactivate IDS
IDS -> IDS : ID, BBox값 생성  
activate IDS
deactivate IDS
IDS ->> Main : FOD 정보 전송 \n{ ID, 타입, BBox값, 카메라 ID, 이미지 ID }
deactivate IDS

Main -> Main : BBox값을 좌표(x,y)로 변환
activate Main
deactivate Main
Main -> DB : 전체 구역 좌표 요청 
activate DB
DB -> DB : FALCON DB 정보 조회
activate DB
deactivate DB
DB --> Main : 정보 응답
deactivate DB
Main -> Main : 구역 판단(RWY A구역)
activate Main
deactivate Main
Main -> Main : RWY A구역 상태(정상 -> 위험)\nFOD와 일치하는 이미지 ID의 이미지를 버퍼에서 추출
activate Main
deactivate Main

Main ->> GUI : RWY A구역 상태 전송 
activate GUI
GUI -> GUI : RWY A구역 상태 업데이트 
activate GUI
deactivate GUI
deactivate GUI
Main ->> PM : RWY A구역 상태 전송 
activate PM
PM -> PM : RWY A구역 상태 업데이트 
activate PM
deactivate PM
deactivate PM


Main -> DB : [ID 최초 시] 정보 저장\n{이미지, ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각}
activate DB
DB -> DB : FALCON DB에 정보 저장 
activate DB
deactivate DB
DB --> Main : 저장 완료
deactivate DB


Main ->>GUI : FOD 정보 전송 {객체 ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각} \n
deactivate Main
activate GUI
GUI -> GUI : FOD 정보 감지목록에 업데이트
activate GUI
deactivate GUI
GUI -> GUI : [ID 최초 시] 팝업 생성
activate GUI
deactivate GUI
deactivate GUI




@enduml

---

@startuml
title  위험요소 FOD 처리완료

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "ATC GUI" as GUI
participant "Pilot GUI" as PM

activate Main
Main -> Main : RWY A 구역 감지 해제 타이머 시작(2초)
activate Main
deactivate Main
loop 
  -> IDS 
  activate IDS
  IDS -> IDS : 이미지 프레임 수신
  activate IDS
  deactivate IDS
  IDS -> IDS : 이미지 분석\n(FOD 감지 안됨)
  activate IDS
  deactivate IDS
end

deactivate IDS
Main -> Main :  감지 해제 타이머 경과
activate Main
deactivate Main
Main -> Main : RWY A 구역 상태\n(위험->정상)
activate Main
deactivate Main
Main ->> GUI : RWY A 구역 상태 전송 
activate GUI
GUI -> GUI : RWY A 구역 상태 업데이트 \n(위험->정상)
activate GUI
deactivate GUI
deactivate GUI
Main -> PM : RWY A 구역 상태 전송
activate PM
deactivate Main
PM -> PM : RWY A 구역 상태 업데이트[위험->정상]
activate PM
deactivate PM
deactivate PM


@enduml

---

@startuml
title SC_04. 위험요소 상세정보 조회

actor 관제사
participant "Admin GUI" as GUI
participant "Main Server" as Main
participant "DB Manager" as DB

관제사 -> GUI : Map에 있는 위험요소 or\n 감지목록에 있는 위험요소 클릭
activate GUI
GUI -> Main : 위험요소 상세정보 요청
deactivate GUI

activate Main
Main -> DB : 위험요소 상세정보 요청

activate DB
DB -> DB : ID에 맞는 FALCON DB 정보 조회
activate DB
deactivate DB
DB --> Main : 위험요소 상세정보 응답\n{이미지, 이벤트 타입, 구역, 객체 ID, 객체 Type, 감지 시각} 반환

deactivate DB

Main --> GUI : 위험요소 상세정보 응답
deactivate Main

activate GUI
GUI -> GUI : 위험요소 상세정보 업데이트
activate GUI
GUI -> 관제사 : 위험요소 상세정보 시현
deactivate GUI

@enduml

---

@startuml
title SC_04. 위험요소 상세정보 조회 (오류 처리 시나리오)

actor 관제사
participant "Admin GUI" as GUI
participant "Main Server" as Main
participant "DB Manager" as DB

관제사 -> GUI : Map에 있는 위험요소 or\n감지목록에 있는 위험요소 클릭
activate GUI
GUI -> Main : 위험요소 상세정보 요청
deactivate GUI

activate Main
Main -> DB : 위험요소 상세정보 요청

activate DB
DB -> DB : ID에 맞는 FALCON DB 정보 조회  
activate DB
deactivate DB
DB --> Main : 위험요소 조회 실패 응답
deactivate DB

Main --> GUI : 위험요소 상세정보 조회 실패 응답 \n(에러 코드, 메시지)
deactivate Main

activate GUI
deactivate GUI
GUI -> 관제사 : 오류 알림 팝업 표시
deactivate GUI
@enduml

---

@startuml
title SC_03. 쓰러진 인원 감지 

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "DB Manager" as DB
participant "Admin GUI" as GUI
participant "Pilot GUI" as PM


-> IDS
activate IDS
IDS -> IDS : 이미지 프레임 수신
activate IDS
deactivate IDS
IDS ->> Main : 이미지 전송\n {카메라 ID, 이미지 ID, 이미지}
activate Main
Main -> Main : 이미지 버퍼에 저장  
activate Main
deactivate Main
IDS -> IDS : 이미지 분석\n(작업자, 일반인 구분 및 자세 감지)
activate IDS
deactivate IDS
IDS -> IDS : ID, BBox값 생성  
activate IDS
deactivate IDS
IDS ->> Main : 인간 정보 전송 \n{ ID, 타입, BBox값, 카메라 ID, 이미지 ID, 자세}
deactivate IDS

Main -> DB : 전체 구역 좌표 요청 
activate DB
DB -> DB : FALCON DB 정보 조회
activate DB
deactivate DB
DB --> Main : 정보 응답
deactivate DB
Main -> Main : 구역 판단(RWY B구역)
activate Main
deactivate Main
Main -> Main : RWY B구역 (정상 -> 위험)\n구조인원와 일치하는 이미지 ID의 이미지를 버퍼에서 추출
activate Main
deactivate Main

Main ->> GUI : RWY B구역 상태 전송 
activate GUI
GUI -> GUI : RWY B구역 상태 업데이트 
activate GUI
deactivate GUI
deactivate GUI

Main ->> PM : RWY B구역 상태 전송 
activate PM
PM -> PM : RWY B구역 상태 업데이트 
activate PM
deactivate PM
deactivate PM


Main -> DB : [ID 최초 시] 정보 저장\n{이미지, ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각}
activate DB
DB -> DB : FALCON DB에 정보 저장 
activate DB
deactivate DB
DB --> Main : 저장 완료
deactivate DB


Main ->>GUI : 구조인원 정보 전송 {객체 ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각} \n
deactivate Main
activate GUI
GUI -> GUI : 구조인원 정보 감지목록에 업데이트
activate GUI
deactivate GUI
GUI -> GUI : [ID 최초 시] 팝업 생성
activate GUI
deactivate GUI
deactivate GUI

@enduml


---

@startuml
title  쓰러진 인원 구조 완료

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "ATC GUI" as GUI
participant "Pilot GUI" as PM

activate Main
Main -> Main : RWY B 구역 감지 해제 타이머 시작(2초)
activate Main
deactivate Main
loop 
  -> IDS 
  activate IDS
  IDS -> IDS : 이미지 프레임 수신
  activate IDS
  deactivate IDS
  IDS -> IDS : 이미지 분석\n(구조인원 감지 안됨)
  activate IDS
  deactivate IDS
end

deactivate IDS
Main -> Main :  감지 해제 타이머 경과
activate Main
deactivate Main
Main -> Main : RWY B 구역 상태\n(위험->정상)
activate Main
deactivate Main
Main ->> GUI : RWY B 구역 상태 전송 
activate GUI
GUI -> GUI : RWY B 구역 상태 및 감지목록 업데이트 \n(위험->정상)
activate GUI
deactivate GUI
deactivate GUI
Main ->> PM : RWY B 구역 상태 전송
deactivate Main
activate PM
PM -> PM : RWY B 구역 상태 업데이트\n[위험->정상]
activate PM
deactivate PM
deactivate PM


@enduml

---

@startuml
title SC_02. 출입 위반 인원 감지 

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "DB Manager" as DB
participant "Admin GUI" as GUI
participant "Pilot GUI" as PM


-> IDS
activate IDS
IDS -> IDS : 이미지 프레임 수신
activate IDS
deactivate IDS
IDS ->> Main : 이미지 전송\n {카메라 ID, 이미지 ID, 이미지}
activate Main
Main -> Main : 이미지 버퍼에 저장  
activate Main
deactivate Main
IDS -> IDS : 이미지 분석\n(작업자, 일반인 구분 및 자세 감지)
activate IDS
deactivate IDS
IDS -> IDS : ID, BBox값 생성  
activate IDS
deactivate IDS
IDS ->> Main : 일반인 정보 전송 \n{ ID, 타입, BBox값, 카메라 ID, 이미지 ID, 자세}
deactivate IDS

Main -> DB : 전체 구역 좌표 및 출입조건 요청 
activate DB
DB -> DB : FALCON DB 정보 조회
activate DB
deactivate DB
DB --> Main : 정보 응답
deactivate DB

Main -> Main : 구역 및 출입 위반 판단\n(RWY B구역 일반인 접근 불가)
activate Main
deactivate Main
Main -> Main : RWY B구역 (정상 -> 위험)\n위반인원과 일치하는 이미지 ID의 이미지를 버퍼에서 추출
activate Main
deactivate Main
Main ->> GUI : RWY B구역 상태 전송 
activate GUI
GUI -> GUI : RWY B구역 상태 업데이트 
activate GUI
deactivate GUI
deactivate GUI

Main ->> PM : RWY B구역 상태 전송 
activate PM
PM -> PM : RWY B구역 상태 업데이트 
activate PM
deactivate PM
deactivate PM


Main -> DB : [ID가 최초 or 이전 감지구역이 출입허용구역일때] \n정보 저장 {이미지, ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각}
activate DB
DB -> DB : FALCON DB에 정보 저장 
activate DB
deactivate DB
DB --> Main : 저장 완료
deactivate DB


Main ->>GUI : 위반인원 정보 전송 {객체 ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각} \n
deactivate Main
activate GUI
GUI -> GUI : 위반인원 정보 감지목록에 업데이트
activate GUI
deactivate GUI
GUI -> GUI : [ID 최초 시] 팝업 생성
activate GUI
deactivate GUI
deactivate GUI

@enduml

---

@startuml
title SC_02. 출입 위반 인원 감지 해제

participant "Image Detecting Server" as IDS
participant "Main Server" as Main
participant "DB Manager" as DB
participant "Admin GUI" as GUI
participant "Pilot GUI" as PM


-> IDS
activate IDS
IDS -> IDS : 이미지 프레임 수신
activate IDS
deactivate IDS
IDS ->> Main : 이미지 전송\n {카메라 ID, 이미지 ID, 이미지}
activate Main
Main -> Main : 이미지 버퍼에 저장  
activate Main
deactivate Main
IDS -> IDS : 이미지 분석\n(작업자, 일반인 구분 및 자세 감지)
activate IDS
deactivate IDS
IDS -> IDS : ID, BBox값 생성  
activate IDS
deactivate IDS
IDS ->> Main : 일반인 정보 전송 \n{ ID, 타입, BBox값, 카메라 ID, 이미지 ID, 자세}
deactivate IDS


Main -> DB : 전체 구역 좌표 및 출입조건 요청 
activate DB
DB -> DB : FALCON DB 정보 조회
activate DB
deactivate DB
DB --> Main : 정보 응답
deactivate DB

Main -> Main : 구역 및 출입 위반 판단(Ramp 구역 일반인 접근 가능)
activate Main
deactivate Main
Main -> Main : RWY B구역 (위험 -> 정상)
activate Main
deactivate Main

Main ->> GUI : RWY B구역 상태 전송 
activate GUI
GUI -> GUI : RWY B구역 상태 업데이트 
activate GUI
deactivate GUI
deactivate GUI

Main ->> PM : RWY B구역 상태 전송 
activate PM
PM -> PM : RWY B구역 상태 업데이트 
activate PM
deactivate PM
deactivate PM

Main ->>GUI : 일반인 정보 전송 {객체 ID, 타입, 이벤트 타입, 좌표, 구역, 감지 시각} \n
deactivate Main
activate GUI
GUI -> GUI : 감지목록 업데이트
activate GUI
deactivate GUI
deactivate GUI

@enduml


---

@startuml
title SC_05. CCTV A 영상 조회 클릭

actor 관제사
participant "Admin GUI" as GUI

participant "Main Server" as Main
participant "IDS " as IDS
관제사 -> GUI : CCTV A 보기 버튼 클릭
activate GUI
GUI -> Main : CCTV A 영상 요청(TCP)
deactivate GUI
activate Main
Main -> Main : CCTV A 영상 송신 상태(ON)\n CCTV B 영상 송신 상태(OFF)
activate Main
deactivate Main

Main --> GUI : 응답성공
deactivate Main
activate GUI






IDS ->> Main : 이미지 프레임 전송\n{카메라 ID,이미지 ID,이미지}
activate Main
Main -> Main : 감지된 객체 BBox와 이미지를 이미지 ID로 매칭 
activate Main
deactivate Main
Main ->> GUI : 매칭된 이미지를 송신{카메라 ID,이미지 ID,이미지}
deactivate Main
GUI ->> 관제사 : CCTV A 영상 시현
deactivate GUI

@enduml

---

@startuml
title SC_05. CCTV A 영상 조회 실패

actor 관제사
participant "Admin GUI" as GUI
participant "Main Server" as Main
관제사 -> GUI : CCTV A 보기 버튼 클릭
activate GUI
GUI -> Main : CCTV A 영상 요청
deactivate GUI
activate Main
Main -> Main : CCTV A 영상 송신 상태(ON)\n CCTV B 영상 송신 상태(OFF)
activate Main
deactivate Main
Main --> GUI : CCTV 영상 수신 실패 응답
activate GUI
GUI -> 관제사 : 팝업 표시 (CCTV 영상 수신 실패)
deactivate GUI


@enduml


---

@startuml
title SC_09 - 출입조건 설정

actor 관제사
participant "Admin GUI" as GUI
participant "Main Server" as Main
participant "DB Manager" as DB


관제사 -> GUI : 출입 설정 페이지 클릭
activate GUI
GUI -> Main : 전체구역 출입조건 조회 요청
deactivate GUI
activate Main
Main -> DB : 전체구역 출입조건 조회
activate DB

DB -> DB : FALCON DB 출입조건 조회
activate DB
deactivate DB
DB --> Main : 전체구역 출입조건 반환
deactivate DB
Main --> GUI : 전체구역 출입조건 응답
deactivate Main
activate GUI
GUI -> GUI : 전체구역 출입조건 업데이트 
activate GUI
deactivate GUI
GUI --> 관제사 : 출입 설정 페이지 시현
deactivate GUI




관제사 -> GUI : RWY A 구역 클릭 
activate GUI
GUI --> 관제사 : RWY A 출입설정 창 시현
deactivate GUI

관제사 -> GUI : RWY A 구역 출입조건 수정 후 설정 
activate GUI

GUI -> Main : 변경 출입조건 저장 요청
deactivate GUI

activate Main
Main -> Main : 유효성 검사
activate Main
deactivate Main

alt 유효성 통과
    Main -> DB : 출입조건 업데이트
    activate DB
    DB -> DB : FALCON DB 출입조건 업데이트
    activate DB
    deactivate DB
    DB --> Main : 처리 결과 반환
    deactivate DB
    Main --> GUI : 완료 메시지
    deactivate Main

    activate GUI
    GUI -> GUI : 출입조건 업데이트 팝업 알림
    activate GUI
    deactivate GUI
    GUI --> 관제사 : 업데이트 화면시현 및 팝업 알림
    deactivate GUI

else 유효성 실패
    Main --> GUI : 오류 메시지 전송
    deactivate Main
    GUI --> 관제사 : 설정 오류 알림
end

@enduml


---

@startuml
title SC_06. 실시간 조류 충돌 위험도 산정 및 시각화

participant "Bird Detecting Server(BDS)" as BDS
participant "Main Server" as Main
participant "DB Manager" as DB
participant "ATC GUI" as GUI
participant "Pilot GUI" as PilotGUI


-> BDS : 이미지 프레임 수신\n{카메라 ID: A/B, 이미지 ID: img_n}

activate BDS
BDS -> BDS : 위험 점수 및 등급 산출\n

alt 위험도 등급 변경 시
  BDS ->> Main : 변경된 위험도 등급 전송\n{type: "event", event: "BR_CHANGED", result: "BR_XX"}
  activate Main
  Main -> DB : 위험도 변경 이력 저장\n{timestamp, level}
  activate DB
  DB -> DB : FALCON DB에 위험도 변경 이력 저장
  DB --> Main : 저장 완료
  deactivate DB
  Main ->> GUI : 위험도 등급 전송
  activate GUI
  GUI -> GUI : 위험도 상태 업데이트
  deactivate GUI

  Main ->> PilotGUI : 위험도 등급 전송
  activate PilotGUI
  PilotGUI -> PilotGUI : 위험도 상태 업데이트
  deactivate PilotGUI

  
end



deactivate Main
@enduml


---

@startuml
title SC_07. 조종사 TCP 요청-응답 흐름

participant "Pilot GUI" as GUI
participant "VoiceManager" as VM
participant "Main Server" as Main
participant "DB Manager" as DB

activate GUI
-> GUI : 마이크 버튼 클릭
-> GUI : 음성 질의 입력
GUI -> VM : 음성 데이터 전송\n
deactivate GUI

activate VM
VM -> VM : STT 음성 처리 (Whisper)
VM -> VM : 조종사 요청 분류 (RequestClassifier)

VM -> Main : TCP 명령어 전송\n{ type: "command", command: "BR_INQ" }

activate Main
Main -> DB : 위험도 등급 조회\n
DB -> DB : FALCON DB에서 위험도 등급 조회
DB --> Main : 위험도 등급 조회 결과 반환\n

Main --> VM : TCP 응답 반환\n{ type: "response", command: "BR_INQ", result: "BR_HIGH" }
deactivate Main

VM -> VM : 응답 문장 생성\n("Bird activity high. Hold for approach.")
VM -> VM : TTS 음성 변환\n

VM --> GUI : 음성 데이터 전송\n
activate GUI
GUI -> GUI : 음성 응답 출력
activate GUI
deactivate VM
deactivate GUI
deactivate GUI

@enduml


---

@startuml
title SC_11 - 실시간 조류 위험도 이벤트 알림

participant "FALCON Main Server" as FALCON
participant "RedWing Main Server" as RWS
participant "RedWing GUI" as GUI


FALCON -> RWS : 위험도 이벤트 브로드캐스트\n{"event": "BR_CHANGED", "result": "BR_HIGH"}
deactivate FALCON
activate RWS

RWS -> RWS : 이벤트 처리 및 필터링
deactivate RWS

RWS -> GUI : 조류 위험도 이벤트 전달
activate GUI

GUI -> GUI : 녹음 상태 확인\n(음성 처리 중이면 차단)

alt 음성 처리 중이 아님
    GUI -> GUI : TTS 생성 및 음성 출력\n"WARNING. Bird risk high. Advise extreme vigilance."
    GUI -> GUI : 화면 업데이트\n
else 음성 처리 중임
    GUI -> GUI : TTS 차단\n
    GUI -> GUI : 화면만 업데이트
end

deactivate GUI
@enduml

---

@startuml
title SC_10 - 마샬링 제스처 인식

participant "RedWing GUI" as GUI
participant "RedWing Main Server" as RWS
participant "PDS Server" as PDS

-> GUI : START MARSHAL 버튼 클릭
activate GUI
GUI -> RWS : 마샬링 시작 명령\n{"command": "MARSHALING_START"}
deactivate GUI

activate RWS
RWS -> PDS : 마샬링 활성화 명령 전달
deactivate RWS

activate PDS
PDS -> PDS : 카메라 활성화
PDS -> PDS : MediaPipe 포즈 추정 시작
PDS -> PDS : 실시간 포즈 데이터 수집
PDS -> PDS : TCN 모델 예측
PDS -> PDS : 제스처 확신도 검증\n
PDS -> RWS : 제스처 이벤트 전송\n{"event": "MARSHALING_GESTURE_DETECTED", "result": "STOP"}
deactivate PDS

activate RWS
RWS -> GUI : 제스처 이벤트 전송\n{"event": "MARSHALING_GESTURE_DETECTED", "result": "STOP"}
deactivate RWS

activate GUI
GUI -> GUI : TTS 음성 알림 생성
GUI -> GUI : 유도 동작 음성 안내
deactivate GUI


@enduml

---

@startuml
title SC_08 - 지상 위험 요소 감지 이력 조회 

actor 관제사
participant "Admin GUI" as GUI
participant "Main Server" as Main
participant "DB Manager" as DB


관제사 -> GUI : 이력 조회 페이지 클릭
activate GUI
GUI --> 관제사 : 이력 조회 페이지 시현
deactivate GUI

관제사 -> GUI : 지상 위험 요소 감지 이력 클릭
activate GUI
GUI --> 관제사 : 지상 위험 요소 감지 이력 페이지 시현
deactivate GUI

관제사 -> GUI : 날짜(Default:일주일) 및 \n타입(Default: 전체) 선택 후 조회 클릭
activate GUI
GUI -> Main : 지상 위험 요소 감지 이력 요청
deactivate GUI
activate Main
Main -> DB : 조건 기반 이력 검색
activate DB
DB -> DB : FALCON DB 이력 조회
activate DB
deactivate DB
DB --> Main : 이력 응답
deactivate DB
Main -> GUI : 이력 결과 전달
deactivate Main

activate GUI
GUI -> GUI :  지상 위험 요소 감지 이력 업데이트{ID, 타입, 이벤트타입, 감지구역, 감지시각}
activate GUI
deactivate GUI
GUI --> 관제사 : 지상 위험 요소 감지 이력 시현
deactivate GUI 

@enduml

---

