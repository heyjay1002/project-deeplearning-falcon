import os
from collections import Counter

# YOLO 라벨 파일들이 있는 루트 디렉터리
ROOT = r"C:\Users\Administrator\Downloads\merged_dataset\fine_tune_dataset"

# labels 디렉터리 경로 모으기
label_dirs = [
    os.path.join(ROOT, 'labels')  # fine_tune_dataset/labels 안만 확인
]


class_counter = Counter()

for label_dir in label_dirs:
    if not os.path.isdir(label_dir):
        continue

    for file in os.listdir(label_dir):
        if file.endswith(".txt"):
            file_path = os.path.join(label_dir, file)
            with open(file_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) > 0:
                        class_id = int(parts[0])  # 첫 번째 값이 클래스 ID
                        class_counter[class_id] += 1

# 결과 출력
print("📊 클래스별 객체 수:")
for class_id, count in sorted(class_counter.items()):
    print(f"클래스 {class_id}: {count}개")
    