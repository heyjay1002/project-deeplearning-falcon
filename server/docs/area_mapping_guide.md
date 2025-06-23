# Area Mapping Guide

## 1. 개요

이 문서는 객체 검출 결과(bbox 중심점)를 맵 상의 AREA(구역)와 연관시키는 원리와 활용법을 설명합니다. 본 가이드는 시스템의 좌표화(픽셀→구역) 로직을 명확히 이해하고, 유지보수 및 확장에 도움을 주기 위해 작성되었습니다.

**✅ 구현 완료**: 픽셀 좌표화 시스템이 성공적으로 구현되어 실시간으로 동작 중입니다.

---

## 2. 기본 개념

### 2.1 bbox 중심점
- 객체 검출(bbox) 결과는 [x1, y1, x2, y2] 형태의 픽셀 좌표로 제공됩니다.
- 중심점(center_x, center_y)은 다음과 같이 계산합니다:
  - center_x = (x1 + x2) / 2
  - center_y = (y1 + y2) / 2
- 이 중심점은 프레임(맵 이미지) 상에서 객체의 위치를 나타냅니다.

### 2.2 AREA(구역)
- AREA는 맵(프레임) 상의 특정 사각형 영역을 의미합니다.
- DB의 AREA 테이블 구조 예시:

| area_id | area_name | x1   | y1   | x2   | y2   |
|---------|-----------|------|------|------|------|
|   1     | TWY_A     |  0   | 0.22 | 0.19 | 0.52 |
|   2     | TWY_B     | 0.81 | 0.22 | 1    | 0.52 |
| ...     | ...       | ...  | ...  | ...  | ...  |

- (x1, y1): 좌상단, (x2, y2): 우하단 (정규화 좌표 0~1)

---

## 3. 매핑 원리

### 3.1 기본 가정
- 맵(프레임)을 바로 위에서 수직으로 본 상태(Top-Down View)로 가정
- 프레임의 픽셀 좌표를 정규화하여 AREA의 좌표계와 일치시킴

### 3.2 매핑 알고리즘
1. **프레임 해상도(픽셀)와 bbox 중심점(픽셀) 확보**
2. **정규화 좌표 변환**: 픽셀 좌표를 0~1 범위로 변환
3. **맵 좌표 변환**: 정규화 좌표를 맵 크기(960x720)에 맞게 변환
4. **각 AREA의 좌표(x1, y1, x2, y2) 정보 확보**
5. **중심점이 어느 AREA에 속하는지 판별**

```python
# 좌표 변환 함수 (실제 구현됨)
def convert_to_map_coords(self, center_x, center_y, frame_width, frame_height):
    norm_x = center_x / frame_width      # 정규화 좌표
    norm_y = center_y / frame_height
    map_x = norm_x * config.MAP_WIDTH    # 맵 좌표 (960 기준)
    map_y = norm_y * config.MAP_HEIGHT   # 맵 좌표 (720 기준)
    return map_x, map_y, norm_x, norm_y

# 구역 매핑 함수 (실제 구현됨)
def find_area_id(self, norm_x, norm_y):
    for area in self.area_list:
        if area['x1'] <= norm_x <= area['x2'] and area['y1'] <= norm_y <= area['y2']:
            return area['area_id']
    return None
```

- 여러 AREA가 겹칠 경우, 첫 번째 매칭 AREA를 사용

---

## 4. 활용 예시

### 4.1 DB 저장
- **DB에는 map_x, map_y 필드에 변환된 맵 좌표(960x720 기준)를 저장합니다.**
- area_id 필드에 해당 구역 정보를 함께 저장합니다.
- map_x, map_y는 GUI에서 바로 사용할 수 있는 맵 좌표입니다.
- 객체의 area_id를 함께 저장하여, 이후 통계/알람/시각화 등에 활용할 수 있습니다.

### 4.2 GUI/알람
- 객체가 특정 AREA에 진입/이탈할 때 이벤트 발생
- AREA별 객체 분포 시각화
- 실시간 좌표 정보 표시

### 4.3 메시지 포맷
```
ME_FD: {object_id},{class},{map_x},{map_y},{area_name},{timestamp}
```

---

## 5. 확장 및 주의사항

- **실세계 좌표 변환**이 필요한 경우, AREA 좌표를 실세계 단위(미터 등)로 변환하는 추가 매핑이 필요함
- **좌표계 일치**: 프레임과 AREA의 좌표계(픽셀/정규화)가 반드시 일치해야 함
- **카메라 왜곡/기울기**가 있는 경우, 보정 로직 추가 필요

---

## 6. 구현 상태

### ✅ 완료된 기능
- [x] bbox 중심점 계산 로직
- [x] 픽셀 → 정규화 좌표 변환
- [x] 정규화 → 맵 좌표 변환
- [x] 구역 매핑 알고리즘
- [x] DB 연동 및 저장
- [x] GUI 실시간 좌표 표시
- [x] 에러 처리 및 로깅

### 🔄 향후 개선 사항
- [ ] 실세계 좌표 변환 (미터 단위)
- [ ] 다중 카메라 좌표 통합
- [ ] 3D 공간 좌표 변환
- [ ] 동적 구역 생성/수정 기능

---

## 7. 참고
- [Detection Buffer Guide](./detection_buffer_guide.md)
- [코드 구조 가이드](./code_structure.md)
- [픽셀 좌표화 진척도 보고서](./pixel_coordinate_progress_report.md)

---

본 문서는 시스템의 AREA 매핑(좌표화) 로직을 명확히 기록하기 위해 작성되었습니다. 추가 개선/확장 시 이 문서를 업데이트해 주세요. 