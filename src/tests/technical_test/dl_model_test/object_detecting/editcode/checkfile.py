import os
from collections import defaultdict

# 경로 설정
dataset_path = r"C:\Users\Administrator\Downloads\merged_dataset\fine_tune_dataset"
splits = ["train", "valid", "test"]

class_counts = defaultdict(int)         # 클래스별 총 객체 수
class_file_counts = defaultdict(set)    # 클래스별 등장한 파일 이름 집합

for split in splits:
    label_dir = os.path.join(dataset_path, split, "labels")
    if not os.path.exists(label_dir):
        print(f"❌ {split}/labels 디렉토리 없음")
        continue

    for label_file in os.listdir(label_dir):
        if not label_file.endswith(".txt"):
            continue

        label_path = os.path.join(label_dir, label_file)
        with open(label_path, 'r') as f:
            lines = f.readlines()
            seen_in_file = set()  # 중복 클래스 방지

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 1:
                    class_id = parts[0]
                    class_counts[class_id] += 1
                    seen_in_file.add(class_id)

            for class_id in seen_in_file:
                class_file_counts[class_id].add(label_file)

# 결과 출력
print("\n📊 fine_tune_dataset 클래스별 요약:")
for class_id in sorted(class_counts.keys(), key=int):
    total_obj = class_counts[class_id]
    file_count = len(class_file_counts[class_id])
    print(f" - 클래스 {class_id}: {total_obj}개 객체 / {file_count}개 파일에 등장")
