# IDS 프로토콜

## 1. UDP 통신 (포트 4000)

### 영상 스트림
```
포맷: {cam_id}:{img_id}:{binary_img}
예시: A:1718135772191843820:frame

필드 설명:
- cam_id: 카메라 식별자 ('A', 'B')
- img_id: 프레임 번호 (나노초 19자리)
- binary_img: OpenCV VideoCapture.read()로 읽은 바이너리 이미지
```

## 2. TCP 통신 (포트 5000)

### 객체 감지 이벤트
```json
{
  "type": "event",
  "event": "object_detected",
  "camera_id": "A",
  "img_id": 1718135772191843820,
  "detections": [
    {
      "object_id": 1001,
      "class": "person",
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.92,
      "pose": "stand"  // 사람인 경우에만
    }
  ]
}
```

### 마커 감지 이벤트
```json
{
  "type": "event",
  "event": "marker_detected",
  "camera_id": "A",
  "markers": [
    {
      "marker_id": "A",  // 맵의 좌상단부터 DEF ABC 순
      "position": [x, y]
    }
  ]
}
```

### 모드 설정 응답
```json
{
  "type": "response",
  "response": "set_mode",
  "mode": "objet_detect"
}
```

### 모드 설정 명령 (서버 → IDS)
```json
{
  "type": "command",
  "command": "set_mode_object"
}
```

### 모드 설정 응답 (IDS → 서버)
```json
{
  "type": "response",
  "command": "set_mode_object",
  "result": "ok"
}
``` 