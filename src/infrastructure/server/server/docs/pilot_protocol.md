# 조종사 GUI 프로토콜

## TCP 통신 (포트 5300)

### 1. 이벤트 메시지 (서버 → GUI)
```json
{
  "type": "event",
  "event": "BIRD_RISK_LEVEL_CHANGED",
  "changed_level": "BIRD_RISK_HIGH",
  "source": "pilot_gui"
}
```

### 2. 요청 메시지 (GUI → 서버)
```json
{
  "type": "command",
  "command": "query_information",
  "request_code": "BIRD_RISK_INQUIRY",
  "source": "pilot_gui"
}
```

#### 요청 코드 종류
- `BR_INQ`: 조류 위험도 조회
- `RWY_A_STATUS`: 활주로 알파 상태 조회
- `RWY_B_STATUS`: 활주로 브라보 상태 조회
- `RWY_AVAIL_IN`: 사용 가능 활주로 조회

### 3. 응답 메시지 (서버 → GUI)
```json
{
  "type": "response",
  "status": "success",
  "request_code": "BIRD_RISK_INQUIRY",
  "response_code": "BIRD_RISK_HIGH",
  "source": "main_server"
}
```

#### 응답 코드 종류

1. 조류 위험도
   - `BR_HIGH`
   - `BR_MEDIUM`
   - `BR_LOW`

2. 활주로 상태
   - `CLEAR`
   - `BLOCKED`

3. 사용 가능 활주로
   - `ALL`
   - `A_ONLY`
   - `B_ONLY`
   - `NONE` 