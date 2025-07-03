import os

BASE_DIR = r"C:\Users\Administrator\Downloads\newdataset"

def check_image_label_match(subfolder):
    for split in ["train", "valid", "test"]:
        img_dir = os.path.join(subfolder, split, "images")
        lbl_dir = os.path.join(subfolder, split, "labels")

        if not os.path.exists(img_dir) or not os.path.exists(lbl_dir):
            continue

        img_files = [os.path.splitext(f)[0] for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        lbl_files = [os.path.splitext(f)[0] for f in os.listdir(lbl_dir) if f.lower().endswith(".txt")]

        img_only = sorted(set(img_files) - set(lbl_files))
        lbl_only = sorted(set(lbl_files) - set(img_files))

        print(f"\n📁 {os.path.basename(subfolder)} / {split}")
        print(f" - 이미지 수: {len(img_files)} | 라벨 수: {len(lbl_files)}")
        print(f" - ⚠️ 라벨 없는 이미지: {len(img_only)}")
        print(f" - ⚠️ 이미지 없는 라벨: {len(lbl_only)}")

        if img_only:
            print("   → 라벨 없는 이미지 예시:", img_only[:5])
        if lbl_only:
            print("   → 이미지 없는 라벨 예시:", lbl_only[:5])

# 전체 클래스 폴더 순회
for folder in os.listdir(BASE_DIR):
    full_path = os.path.join(BASE_DIR, folder)
    if os.path.isdir(full_path):
        check_image_label_match(full_path)

print("\n✅ 매칭 검사 완료")
