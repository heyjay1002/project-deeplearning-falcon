# BDS 프로토콜

## TCP 통신 (포트 5200)

### 조류 위험도 이벤트
```json
{
  "type": "event",
  "event": "bird_level_changed",
  "level": 3  // 위험도 단계(1,2,3)
}
```

### 위험도 레벨 설명
- 1: 높음 (HIGH)
- 2: 중간 (MEDIUM)
- 3: 낮음 (LOW) 