# 관제사 GUI 프로토콜

## 1. UDP 통신 (포트 4100)

### 영상 스트림
```
포맷: {cam_id}:{binary_img}
예시: A:frame_box

필드 설명:
- cam_id: 카메라 식별자 ('A', 'B')
- binary_img: OpenCV 바이너리 이미지
```

## 2. TCP 통신 (포트 5100)

### 메시지 형식
```
기본 형식: M[T]_[C]:[DATA]

- T: 메시지 타입
  - E: 이벤트
  - C: 명령
  - R: 응답
- C: 명령 타입
  - OD: 객체 감지
  - BR: 조류 위험
  - MP: 지도
  - CA: CCTV A
  - CB: CCTV B
- DATA: 콤마(,)로 분리된 파라미터들
  - 여러 객체는 세미콜론(;)으로 구분
```

### 이벤트 메시지 (서버 → GUI)

#### 1. 객체 감지
```
형식: ME_OD:{object_id},{class},{x},{y},{zone},{timestamp}[,{state}]
예시: ME_OD:1001,FOD,100,100,RWY_A,2025-06-05T19:21:00Z

필드 설명:
- object_id: 객체 고유 번호 (1, 2, 3...)
- class: 객체 타입 (FOD, person 등)
- x, y: 맵핑된 중심 좌표
- zone: 맵 구역 (RWY_A 등)
- timestamp: ISO 8601 형식 시간
- state: 사람인 경우 상태 (rescue, none)
```

#### 1-1. 최초 객체 감지 (이미지 포함)
```
형식: ME_FD:{object_id},{class},{x},{y},{zone},{timestamp},[{state},]{image_size},{image_binary}
예시(사람): ME_FD:1002,PERSON,200,180,AREA_A,2025-06-05T19:22:00Z,R,12345,<binary_data>
예시(비사람): ME_FD:1001,FOD,100,100,RWY_A,2025-06-05T19:21:00Z,12345,<binary_data>

필드 설명:
- object_id: 객체 고유 번호 (1, 2, 3...)
- class: 객체 타입 (FOD, person 등)
- x, y: 맵핑된 중심 좌표
- zone: 맵 구역 (RWY_A 등)
- timestamp: ISO 8601 형식 시간
- state: 사람인 경우 상태 (R: rescue, N: none)
- image_size: 이미지 바이너리 크기(바이트)
- image_binary: jpg 인코딩된 crop 이미지 데이터
```

#### 2. 조류 위험도
```
형식: ME_BR:{level}
예시: ME_BR:1

- level: 위험도 레벨
  - 1: HIGH
  - 2: MEDIUM
  - 3: LOW
```

#### 3. 활주로 위험도
```
형식: ME_RA:{state} 또는 ME_RB:{state}
예시: ME_RA:0

- state: 활주로 상태
  - 0: 안전
  - 1: 경고
```

### 명령/응답 메시지

#### 1. CCTV 제어
```
요청: MC_CA 또는 MC_CB
응답: MR_CA:OK 또는 MR_CB:OK
```

#### 2. 지도 보기
```
요청: MC_MP
응답: MR_MP:OK
```

#### 3. 상세 보기
```
요청: MC_OD:{object_id}
예시: MC_OD:1001

응답 형식: MR_OD:OK,{object_id},{class},{area},{timestamp},{image_size}$${image_data}
성공 예시: MR_OD:OK,1001,PERSON,RWY_A,2025-06-20T15:30:00Z,12345$$<이미지 바이너리> 

실패 시: MR_OD:ERR,{error_code}

필드 설명:
- object_id: 객체 ID (정수)
- class: 객체 종류 (문자열, 예: `PERSON`, `AIRPLANE`)
- area: 감지 구역 이름 (문자열, 예: `RWY_A`)
- timestamp: 감지 시간 (`YYYY-MM-DDTHH:MM:SSZ` 형식)
- image_size: 뒤따르는 이미지 데이터의 크기 (바이트 단위, 정수)
- $$: 헤더와 이미지 데이터를 구분하는 구분자
- image_data: 실제 이미지 바이너리 데이터
