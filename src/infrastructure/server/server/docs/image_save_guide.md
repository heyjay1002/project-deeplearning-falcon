# 이미지 저장 및 이벤트 송신 가이드

## 1. 전체 데이터 흐름

```
[DetectionProcessor]
    └─(프레임, bbox, object_id)→ [Repository]
        └─(DB 저장 성공 시 콜백)→ [DetectionCommunicator]
            └─(ME_FD 메시지+이미지 바이너리)→ [Admin GUI]
```

- **DetectionProcessor**: 객체 검출 시 프레임, bbox, object_id를 Repository로 전달
- **Repository**: DB에 객체 정보 및 이미지 경로 저장. 저장 성공 시 콜백 호출
- **DetectionCommunicator**: 콜백을 받아, DB에 정상 저장된 객체에 대해 ME_FD(최초 감지 이벤트) 메시지 생성 및 이미지 바이너리와 함께 Admin GUI로 송신
- **Admin GUI**: ME_FD 메시지 수신 후, 이미지와 정보를 팝업 등으로 표시

## 2. 저장 위치 및 파일명
- 모든 crop된 객체 이미지는 `img/` 폴더에 저장
- 파일명: `img_{object_id}.jpg` (object_id는 최초 감지된 객체의 고유 번호)

## 3. 저장 및 송신 시점
- **DB 저장이 성공한 경우에만** 이미지 저장 및 이벤트(ME_FD) 송신
- 중복 감지(object_id 이미 존재) 시에는 저장/송신하지 않음

## 4. 저장 방식
- 프레임에서 bbox([x1, y1, x2, y2])로 crop
- OpenCV 등으로 jpg로 저장

## 5. 예외 처리
- 이미지 저장 실패 시, 로그 기록 및 DB에는 image_path를 비워둠

## 6. 이벤트(ME_FD) 메시지 포맷 및 프로토콜
- **DB 저장 성공 후** DetectionCommunicator가 ME_FD 메시지 생성 및 송신
- **ME_FD 메시지 포맷:**
  - (사람)   `ME_FD:{object_id},{class},{x},{y},{zone},{timestamp},{state},{image_size}$$<image_binary>`
  - (비사람) `ME_FD:{object_id},{class},{x},{y},{zone},{timestamp},{image_size}$$<image_binary>`
- 필드 설명:
  - object_id: 객체 고유 번호
  - class: 객체 타입 (항상 대문자)
  - x, y: 맵핑된 중심 좌표
  - zone: 맵 구역명
  - timestamp: ISO 8601 형식 시간
  - state: (사람인 경우만) R(rescue) 또는 N(none)
  - image_size: 이미지 바이너리 크기(바이트)
  - image_binary: jpg 인코딩된 crop 이미지 데이터
- 실제 전송 시에는 **이미지 파일명 대신 이미지 바이너리(jpg)**가 포함됨

## 7. 각 단계별 책임 및 데이터 전달 방식
- **DetectionProcessor → Repository**: (프레임, bbox, object_id) Python 객체/배열로 직접 전달
- **Repository → DetectionCommunicator**: DB 저장 성공 시 콜백 함수 호출, 객체 정보와 이미지 바이너리 전달
- **DetectionCommunicator → Admin GUI**: TCP 5100 포트로 ME_FD 메시지(바이너리) 송신
- **Admin GUI**: ME_FD 메시지 파싱, 이미지 및 정보 표시

## 8. 참고/확장
- ME_FD 외에 MR_OD 등 유사 이벤트도 동일한 방식으로 확장 가능 (parse_stream_message 등 활용)
- 모든 네트워크 송수신은 config.TCP_BUFFER_SIZE 등 시스템 설정을 따름 