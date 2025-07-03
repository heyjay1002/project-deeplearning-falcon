import os
import json
import shutil
from tqdm import tqdm

# [1] 병합 대상 데이터셋 폴더 목록 정의
dataset_dirs = [
    "0d284ff4c2.v1i.coco-mmdetection",
    "bird1.v3i.coco-mmdetection",
    "CC_Detector4Categorizer_temp1.v2i.coco-mmdetection",
    "CC_DetectorTrainingDataset_temp1.v3i.coco-mmdetection",
    "Dusk.v2i.coco-mmdetection",
    "eagle.v1i.coco-mmdetection",
    "Gull_testing.v1i.coco-mmdetection",
    "hawk.v1i.coco-mmdetection",
]   

# [2] 루트 폴더 위치 (여기에 위 폴더들이 있음)
root_dir = "/home/mac/Downloads/bird/"
output_dir = "/home/mac/Downloads/bird/coco_merged_dataset"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)

# [4] 최종 병합 JSON의 기본 구조 초기화
merged_json = {
    "images": [],
    "annotations": [],
    "categories": [],
}

# [5] ID 충돌 방지를 위해 전역 ID 카운터 설정
img_id = 1      # 이미지 ID 시작 값
ann_id = 1      # 어노테이션 ID 시작 값
category_map = {}  # category name → 새 ID 매핑용 딕셔너리

# [6] 각 데이터셋 폴더 순회
for folder in dataset_dirs:
    for subset in ["train", "valid", "test"]:  # 각각의 서브셋 순회
        # [6-1] JSON 경로 설정
        ann_path = os.path.join(root_dir, folder, "annotations", f"instances_{subset}.json")
        # [6-2] 이미지 경로 설정
        img_folder = os.path.abspath(os.path.join(root_dir, folder, subset))

        if not os.path.exists(ann_path):
            continue  # JSON 파일이 없으면 건너뜀

        # [6-3] COCO JSON 로딩
        with open(ann_path, 'r') as f:
            data = json.load(f)

        # [6-4] 카테고리 매핑 초기화 및 통합
        for cat in data['categories']:
            name = cat['name']
            if name not in category_map:
                new_id = len(category_map) + 1
                category_map[name] = new_id
                # 새로운 카테고리 ID로 병합 JSON에 추가
                merged_json['categories'].append({"id": new_id, "name": name})

        # [6-5] 이미지와 어노테이션 병합 처리
        for img in data['images']:
            old_img_id = img['id']
            # 이미지 파일명 충돌 방지를 위한 리네이밍
            new_file = f"{img_id}_{img['file_name']}"
            src_path = os.path.join(img_folder, img['file_name'])
            dst_path = os.path.join(output_dir, "images", new_file)

            
            # 실제 이미지 복사 수행
            if os.path.exists(src_path):
                shutil.copy(src_path, dst_path)

            # 이미지 정보 추가 (ID와 이름 업데이트)
            merged_json['images'].append({
                "id": img_id,
                "file_name": new_file,
                "width": img.get("width", 0),
                "height": img.get("height", 0),
            })

            # [6-6] 해당 이미지에 속한 어노테이션들만 병합
            for ann in data['annotations']:
                if ann['image_id'] == old_img_id:
                    # category_id도 새 맵 기준으로 매핑
                    cat_name = next(c['name'] for c in data['categories'] if c['id'] == ann['category_id'])
                    new_cat_id = category_map[cat_name]

                    # 어노테이션 추가 (ID, image_id, category_id 모두 재지정)
                    merged_json['annotations'].append({
                        "id": ann_id,
                        "image_id": img_id,
                        "category_id": new_cat_id,
                        "bbox": ann['bbox'],
                        "area": ann.get("area", 0),
                        "segmentation": ann.get("segmentation", []),
                        "iscrowd": ann.get("iscrowd", 0)
                    })
                    ann_id += 1

            img_id += 1  # 다음 이미지 ID 증가

# [7] 병합 결과 저장
with open(os.path.join(output_dir, "instances_merged.json"), "w") as f:
    json.dump(merged_json, f, indent=2)

print(f"✅ Merged {len(dataset_dirs)} datasets into one COCO JSON!")
