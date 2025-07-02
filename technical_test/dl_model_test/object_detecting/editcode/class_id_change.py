import os

# 라벨 변경 대상 루트 디렉터리
ROOT = r"C:\Users\Administrator\Downloads\newdataset"

# 클래스 이름별 ID 매핑
CLASS_NAME_TO_ID = {
    'bird': 0,
    'fod': 1,
    'person': 2,
    'animal': 3,
    'airplane': 4,
    'batcar': 5,
    'coordinateboard': 6,
    'vest': 7,
    'drone': 8
}

# 폴더 이름에서 클래스 추정 (앞부분 포함 시 매칭)
def infer_class_from_folder(foldername: str):
    for key in CLASS_NAME_TO_ID:
        if foldername.lower().startswith(key):
            return key, CLASS_NAME_TO_ID[key]
    return None, None

# 라벨 파일 내 클래스 ID 강제 변경
def update_labels(folder_path, class_name, class_id):
    for split in ["train", "valid", "test"]:
        label_dir = os.path.join(folder_path, split, "labels")
        if not os.path.exists(label_dir):
            continue

        for label_file in os.listdir(label_dir):
            if not label_file.endswith(".txt"):
                continue

            label_path = os.path.join(label_dir, label_file)
            updated_lines = []

            with open(label_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    print(f"⚠️ {label_file} → 무시된 줄: {line.strip()}")
                    continue
                parts[0] = str(class_id)  # 강제로 클래스 ID 덮어쓰기
                updated_lines.append(" ".join(parts))

            if updated_lines:
                with open(label_path, 'w') as f:
                    f.write("\n".join(updated_lines) + "\n")
                print(f"📝 {label_file} → 클래스 ID → {class_id} ({class_name})")

# 전체 서브폴더 순회
for folder in os.listdir(ROOT):
    folder_path = os.path.join(ROOT, folder)
    if not os.path.isdir(folder_path):
        continue

    class_name, class_id = infer_class_from_folder(folder)
    if class_name is not None:
        print(f"\n📂 {folder} → 클래스 '{class_name}' → ID {class_id} 강제 적용 중...")
        update_labels(folder_path, class_name, class_id)
    else:
        print(f"⚠️ {folder} → 클래스 추정 실패 (스킵됨)")

print("\n✅ 라벨 클래스 ID 강제 변경 완료")
