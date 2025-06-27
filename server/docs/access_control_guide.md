# 출입 제어 시스템 가이드

## 개요

공항 관제 시스템의 출입 제어 기능은 감지된 객체를 **위험요소**와 **출입 대상**으로 분류하여, 구역별 권한 설정에 따라 실시간으로 출입 위반을 판별하는 시스템입니다.

## 시스템 구조

### 1. 객체 분류 체계

#### 🚨 위험요소 (Event Type: HAZARD)
- **FOD** (Foreign Object Debris)
- **BIRD** (조류)
- **ANIMAL** (동물)

**특징**: 권한 검증 없이 즉시 위험 알림 전송

#### 👥 출입 대상 (Event Type: UNAUTH, 권한 검증 필요)
- **PERSON** (일반사람)
- **VEHICLE** (일반차량)
- **WORK_PERSON** (작업자)
- **WORK_VEHICLE** (작업차량)

**특징**: 구역별 권한 레벨에 따라 출입 허용/위반 판별

### 2. 권한 레벨 체계

| 권한 레벨 | 레벨명 | 일반용 (PERSON, VEHICLE) | 작업용 (WORK_PERSON, WORK_VEHICLE) |
|-----------|--------|--------------------------|-------------------------------------|
| 1 | OPEN | ✅ 허용 | ✅ 허용 |
| 2 | AUTH_ONLY | ❌ 위반 (경고) | ✅ 허용 |
| 3 | NO_ENTRY | ❌ 위반 (경고) | ❌ 위반 (경고) |

### 3. 구역 설정

시스템은 8개의 고정 구역을 관리합니다:

| 구역 ID | 구역명 | 기본 권한 레벨 |
|---------|--------|----------------|
| 1 | TWY_A | AUTH_ONLY |
| 2 | TWY_B | AUTH_ONLY |
| 3 | TWY_C | AUTH_ONLY |
| 4 | TWY_D | AUTH_ONLY |
| 5 | RWY_A | AUTH_ONLY |
| 6 | RWY_B | AUTH_ONLY |
| 7 | GRASS_A | AUTH_ONLY |
| 8 | GRASS_B | AUTH_ONLY |

## 처리 흐름

### 1. 객체 감지 단계
```
IDS → Main Server: 객체 감지 데이터
├─ 좌표 변환 (픽셀 → 맵 좌표)
├─ 구역 매핑 (좌표 → 구역 ID)
└─ 객체 분류 시작
```

### 2. 객체 분류 단계
```
감지된 객체
├─ 위험요소? (FOD, BIRD, ANIMAL)
│   ├─ Yes: event_type = 1 (HAZARD)
│   └─ 즉시 ME_OD 전송
├─ 항공기? (AIRPLANE, AIRCRAFT)
│   ├─ Yes: 정상 운영 객체
│   └─ 경고하지 않음 (ME_OD 전송 안함)
└─ 출입 대상? (PERSON, VEHICLE, WORK_PERSON, WORK_VEHICLE)
    ├─ Yes: event_type = 2 (UNAUTH, 임시)
    └─ 권한 검증 단계로 이동
```

### 3. 권한 검증 단계
```
출입 대상 객체
├─ 구역 확인
│   ├─ 구역 불명: 위반으로 간주 → ME_OD 전송
│   └─ 구역 확인됨: 권한 레벨 조회
└─ 권한 레벨별 처리
    ├─ OPEN (1): 모든 객체 허용 → ME_OD 전송 안함
    ├─ AUTH_ONLY (2): 
    │   ├─ 작업용: 허용 → ME_OD 전송 안함
    │   └─ 일반용: 위반 → ME_OD 전송
    └─ NO_ENTRY (3): 모든 객체 위반 → ME_OD 전송
```

### 4. 최종 전송 단계
```
ME_OD 전송 대상
├─ 위험요소 (즉시 전송)
└─ 출입 위반 객체 (권한 검증 후 전송)

ME_FD 전송 (DB 저장 완료 시)
├─ event_type: 검증 결과 반영
└─ 이미지와 함께 상세 정보 전송
```

## 프로토콜 명세

### 1. AC_AC (권한 조회)
**요청**: `AC_AC`
**응답**: `AH_AC:level1,level2,level3,level4,level5,level6,level7,level8`

**예시**:
- 요청: `AC_AC`
- 응답: `AH_AC:2,2,2,2,2,2,2,2` (모든 구역 AUTH_ONLY)

### 2. AC_UA (권한 업데이트)
**요청**: `AC_UA:level1,level2,level3,level4,level5,level6,level7,level8`
**응답**: `AH_UA:OK` 또는 `AH_UA:ERROR`

**예시**:
- 요청: `AC_UA:1,2,3,2,2,2,2,2` (구역1=OPEN, 구역3=NO_ENTRY)
- 응답: `AH_UA:OK`

### 3. ME_OD (실시간 객체 정보)
**형식**: `ME_OD:object_id,class,map_x,map_y,area_name[,rescue_level];...`

**예시**:
```
ME_OD:1001,FOD,100,100,TWY_A;1002,PERSON,200,200,RWY_A
```

### 4. ME_FD (최초 감지 알림)
**형식**: `ME_FD:event_type,object_id,class,map_x,map_y,area_name,timestamp[,rescue_level],image_size,<binary_data>`

**예시**:
```
ME_FD:2,1001,PERSON,100,100,TWY_A,2025-06-26T15:30:00Z,0,2048,<이미지 바이너리>
```

## 구현 세부사항

### 1. 캐시 시스템
```python
# 출입 권한 캐시 (메모리 성능 최적화)
self.access_cache = {
    1: 2,  # TWY_A: AUTH_ONLY
    2: 2,  # TWY_B: AUTH_ONLY
    # ... 8개 구역
}
```

### 2. 권한 검증 로직
```python
def _process_detection_with_access_control(self, detections):
    # 1. 객체 분류
    dangerous_objects = []   # 위험요소
    access_objects = []      # 출입 대상
    
    # 2. 권한 검증
    for obj in access_objects:
        authority_level = self.access_cache.get(area_id, 2)
        if authority_level == 1:  # OPEN
            continue  # 전송 안함
        elif authority_level == 2:  # AUTH_ONLY
            if obj_class in ['WORK_PERSON', 'WORK_VEHICLE']:
                continue  # 작업용 허용
            else:
                final_objects_to_send.append(obj)  # 일반용 위반
        elif authority_level == 3:  # NO_ENTRY
            final_objects_to_send.append(obj)  # 모든 객체 위반
    
    # 3. 최종 전송
    self._send_to_gui(final_objects_to_send)
```

### 3. DB 스키마 연동

#### OBJECT_TYPE 테이블
| object_type_id | object_type_name |
|----------------|------------------|
| 0 | BIRD |
| 1 | FOD |
| 2 | PERSON |
| 3 | ANIMAL |
| 4 | AIRPLANE |
| 5 | VEHICLE |
| 6 | WORK_PERSON |
| 7 | WORK_VEHICLE |

#### ACCESS_CONDITIONS 테이블
| area_id | authority_level_id |
|---------|-------------------|
| 1-8 | 1-3 |

#### EVENT_TYPE 테이블
| event_type_id | event_type_name |
|---------------|-----------------|
| 1 | HAZARD |
| 2 | UNAUTH |
| 3 | RESCUE |

## 로그 및 디버깅

### 1. 콘솔 로그 예시
```
[INFO] 위험요소 감지: FOD ID=1001 in Area 1 → 즉시 전송
[INFO] 항공기 감지 (경고 없음): AIRPLANE ID=1002
[INFO] 작업용 접근 허용 (AUTH_ONLY): WORK_PERSON ID=1003 in Area 1
[INFO] 일반용 출입 위반 (AUTH_ONLY): PERSON ID=1004 in Area 1
[INFO] 출입 위반 (NO_ENTRY): WORK_VEHICLE ID=1005 in Area 3
```

### 2. GUI 통신 로그
```
[SEND] ME_OD:1001,FOD,100,100,TWY_A;1003,PERSON,200,200,TWY_A
[SEND] ME_FD:1,1001,FOD,100,100,TWY_A,2025-06-26T15:30:00Z,2048
[SEND] ME_FD:2,1003,PERSON,200,200,TWY_A,2025-06-26T15:30:00Z,0,1024
```

## 운영 가이드

### 1. 권한 설정 변경
1. GUI에서 AC_UA 명령으로 권한 레벨 변경
2. 시스템이 즉시 캐시 업데이트 및 DB 저장
3. 변경 즉시 새로운 권한 적용

### 2. 모니터링 포인트
- 출입 위반 발생률 (구역별)
- 작업용 vs 일반용 객체 비율
- 권한 변경 이력
- 시스템 응답 시간

### 3. 문제 해결
- **ME_OD가 전송되지 않는 경우**: OPEN 구역이거나 작업용 객체의 정당한 접근
- **모든 객체가 위반으로 표시**: NO_ENTRY 설정 확인
- **구역 불명 객체**: 좌표 변환 또는 구역 매핑 문제

## 확장 계획

### 사전 허가 시스템
- 작업 스케줄 연동
- 개별 작업자/차량 ID 관리
- 시간대별 권한 설정

### 위험도 기반 동적 권한
- 조류 위험도와 연동
- 기상 조건 반영
- 비상 상황 자동 대응 