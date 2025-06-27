# Area Mapping Guide

## 1. 개요

이 문서는 객체 검출 결과(bbox 중심점)를 맵 상의 AREA(구역)와 연관시키는 원리와 활용법을 설명합니다. 본 가이드는 시스템의 좌표화(픽셀→구역) 로직을 명확히 이해하고, 유지보수 및 확장에 도움을 주기 위해 작성되었습니다.

**✅ 구현 완료**: 호모그래피 변환 기반 픽셀 좌표화 시스템이 성공적으로 구현되어 실시간으로 동작 중입니다.

---

## 2. 기본 개념

### 2.1 bbox 중심점
- 객체 검출(bbox) 결과는 [x1, y1, x2, y2] 형태의 픽셀 좌표로 제공됩니다.
- 중심점(center_x, center_y)은 다음과 같이 계산합니다:
  - center_x = (x1 + x2) / 2
  - center_y = (y1 + y2) / 2
- 이 중심점은 카메라 프레임 상에서 객체의 위치를 나타냅니다.

### 2.2 AREA(구역)
- AREA는 실제 물리적 공간의 특정 사각형 영역을 의미합니다.
- DB의 AREA 테이블 구조 예시:

| area_id | area_name | x1   | y1   | x2   | y2   |
|---------|-----------|------|------|------|------|
|   1     | TWY_A     |  0   | 0.22 | 0.19 | 0.52 |
|   2     | TWY_B     | 0.81 | 0.22 | 1    | 0.52 |
| ...     | ...       | ...  | ...  | ...  | ...  |

- (x1, y1): 좌상단, (x2, y2): 우하단 (정규화 좌표 0~1)

### 2.3 좌표계 정의
- **실제 맵 크기**: 1800mm × 1350mm (물리적 공간)
- **GUI 맵 크기**: 960 × 720 픽셀 (화면 표시용)
- **정규화 좌표**: 0~1 범위 (구역 정의용)

---

## 3. 호모그래피 변환 기반 매핑 원리

### 3.1 기본 가정
- **카메라 관점**: 각 카메라는 서로 다른 각도와 위치에서 촬영
- **호모그래피 변환**: 카메라 픽셀 좌표를 실제 세계 좌표로 정확히 변환
- **다중 카메라 지원**: 카메라별 개별 보정 데이터 적용

### 3.2 카메라 보정 시스템

#### CalibrationThread 클래스
```python
class CalibrationThread(QThread):
    """맵 보정 처리 전용 스레드"""
    
    def _process_calibration(self, message):
        camera_id = message.get('camera_id')
        matrix = message.get('matrix')
        scale = message.get('scale')
        
        # 보정 데이터 저장
        self.calibration_data[camera_id] = {
            "homography_matrix": np.array(matrix, dtype=np.float64),
            "scale": scale
        }
```

#### 보정 데이터 구조
- **camera_id**: 카메라 식별자 (예: 'A', 'B', 'C')
- **homography_matrix**: 3×3 호모그래피 변환 매트릭스
- **scale**: 스케일 팩터 (필요 시 사용)

### 3.3 좌표 변환 알고리즘

#### 1단계: 호모그래피 변환 (픽셀 → 실제 좌표)
```python
def convert_to_map_coords(self, center_x, center_y, frame_width, frame_height, camera_id='A'):
    # 보정 데이터 확인
    if self.calibration_thread.has_calibration_data(camera_id):
        calibration_data = self.calibration_thread.get_calibration_data(camera_id)
        homography_matrix = calibration_data['homography_matrix']
        
        # 1. 픽셀 좌표를 실제 세계 좌표(mm)로 변환
        pixel_point = np.array([[[center_x, center_y]]], dtype=np.float32)
        world_point = cv2.perspectiveTransform(pixel_point, homography_matrix)
        world_x, world_y = world_point[0][0]
        
        # 2. 실제 세계 좌표를 정규화 좌표로 변환
        norm_x = float(world_x / config.REAL_MAP_WIDTH)   # 1800mm 기준
        norm_y = float(world_y / config.REAL_MAP_HEIGHT)  # 1350mm 기준
        
        # 3. GUI 맵 좌표 계산
        map_x = float(norm_x * config.MAP_WIDTH)    # 960 픽셀 기준
        map_y = float(norm_y * config.MAP_HEIGHT)   # 720 픽셀 기준
        
    return map_x, map_y, norm_x, norm_y
```

#### 2단계: 구역 매핑
```python
def find_area_info(self, norm_x, norm_y, debug=False):
    """정규화 좌표에 해당하는 area 정보 반환"""
    matched_areas = []
    for area in self.area_list:
        if area['x1'] <= norm_x <= area['x2'] and area['y1'] <= norm_y <= area['y2']:
            matched_areas.append(area)
    
    if matched_areas:
        return matched_areas[0]  # 첫 번째 매칭 사용
    return None
```

### 3.4 폴백 시스템 (보정 데이터 없는 경우)
```python
# 보정 데이터가 없는 경우 기본 변환
norm_x = float(center_x / frame_width)
norm_y = float(center_y / frame_height)
map_x = float(norm_x * config.MAP_WIDTH)
map_y = float(norm_y * config.MAP_HEIGHT)
```

---

## 4. 활용 예시

### 4.1 DB 저장
- **map_x, map_y**: GUI에서 바로 사용할 수 있는 맵 좌표 (960×720 기준)
- **area_id**: 해당 구역 정보
- **실제 좌표**: mm 단위의 물리적 위치 정보

```sql
-- 저장되는 좌표 정보
INSERT INTO DETECTION_EVENTS (object_id, map_x, map_y, area_id, ...)
VALUES (1001, 480, 360, 3, ...);
```

### 4.2 GUI/알람
- 객체가 특정 AREA에 진입/이탈할 때 이벤트 발생
- AREA별 객체 분포 시각화
- 실시간 좌표 정보 표시

### 4.3 메시지 포맷
```
ME_FD: {event_type_id},{object_id},{class},{map_x},{map_y},{area_name},{timestamp},{rescue_level},{image_size}
```

---

## 5. 구현 상태

### ✅ 완료된 기능
- [x] 호모그래피 변환 매트릭스 적용
- [x] 카메라별 개별 보정 데이터 관리
- [x] 픽셀 → 실제 좌표(mm) → 정규화 → GUI 좌표 변환
- [x] 구역 매핑 알고리즘
- [x] 다중 카메라 지원
- [x] 폴백 시스템 (보정 데이터 없는 경우)
- [x] DB 연동 및 저장
- [x] GUI 실시간 좌표 표시
- [x] 에러 처리 및 로깅
- [x] CalibrationThread를 통한 비동기 보정 처리

### 🔄 향후 개선 사항
- [ ] 동적 구역 생성/수정 기능
- [ ] 3D 공간 좌표 변환
- [ ] 카메라 보정 GUI 도구
- [ ] 보정 정확도 검증 시스템

---

## 6. 보정 데이터 관리

### 6.1 보정 데이터 수신
```python
def _handle_map_calibration(self, message):
    """맵 보정 메시지 처리"""
    self.calibration_thread.add_calibration_task(message)
```

### 6.2 보정 완료 처리
```python
def _on_calibration_completed(self, camera_id):
    """보정 완료 시그널 처리"""
    print(f"[INFO] 카메라 {camera_id} 보정 완료")
```

### 6.3 보정 데이터 조회
```python
def get_calibration_data(self, camera_id):
    """보정 데이터 조회"""
    return self.calibration_data.get(camera_id)

def has_calibration_data(self, camera_id):
    """보정 데이터 존재 여부 확인"""
    return camera_id in self.calibration_data
```

---

## 7. 확장 및 주의사항

### 7.1 좌표 정확도
- **호모그래피 변환**을 통해 카메라 각도/위치에 관계없이 정확한 실제 좌표 변환
- **보정 데이터 품질**이 전체 시스템 정확도에 결정적 영향

### 7.2 성능 최적화
- **CalibrationThread**: 보정 처리를 별도 스레드에서 비동기 실행
- **캐싱**: 보정 데이터를 메모리에 캐싱하여 빠른 조회

### 7.3 에러 처리
- **보정 데이터 없는 경우**: 기본 변환으로 폴백
- **변환 실패**: 예외 처리 및 로깅
- **다중 매칭**: 첫 번째 매칭 영역 사용, 경고 로그 출력

---

## 8. 참고
- [Detection Buffer Guide](./detection_buffer_guide.md)
- [코드 구조 가이드](./code_structure.md)
- [픽셀 좌표화 진척도 보고서](./pixel_coordinate_progress_report.md)
- [Access Control Guide](./access_control_guide.md)

---

본 문서는 시스템의 호모그래피 변환 기반 AREA 매핑 로직을 명확히 기록하기 위해 작성되었습니다. 추가 개선/확장 시 이 문서를 업데이트해 주세요. 