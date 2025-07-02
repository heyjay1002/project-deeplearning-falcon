@startuml
title 객체 상태 다이어그램

[*] --> DETECTED : 객체 감지됨

DETECTED --> RESCUE_ALERT : 구조 필요 조건 충족
DETECTED --> ENTRY_ALERT : 출입 조건 위반
DETECTED --> HAZARD_ALERT : 위험 조건 충족
ENTRY_ALERT --> DETECTED : 출입 허용 영역으로 이동
ENTRY_ALERT --> CLEARED: 객체 소멸됨
ENTRY_ALERT --> RESCUE_ALERT: 구조 필요 조건 충족
RESCUE_ALERT --> CLEARED : 객체 소멸됨
HAZARD_ALERT --> CLEARED : 객체 소멸됨
DETECTED --> CLEARED : 객체 소멸됨

CLEARED --> [*]
@enduml


---

@startuml
title  GUI 상태 다이어그램

[*] --> disconnect : ATC GUI 시작

disconnect --> connect_uncalibrate : Main Server 연결
connect_uncalibrate --> connect_calibrate : 활주로 맵핑 완료 
connect_uncalibrate--> disconnect :  Main Server 연결 해제
connect_calibrate--> disconnect : Main Server 연결 해제


@enduml
