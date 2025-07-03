import os, shutil, random
from collections import defaultdict
from math import floor

# 📁 폴더 경로
ROOT = r"C:\Users\Administrator\Downloads\merged_dataset"
IMAGE_DIR = os.path.join(ROOT, "train", "images")      # ← 지금은 train 폴더만 대상
LABEL_DIR = os.path.join(ROOT, "train", "labels")

OUT_ROOT   = os.path.join(ROOT, "fine_tune_dataset")
SPLITS     = {"train": 0.8, "valid": 0.1, "test": 0.1}  # 비율 마음대로 조정

# 클래스별 고정 추출 개수
FIXED_COUNT = {0:300, 1:300, 2:300, 3:300, 4:300, 7:300}

# 🔸 출력 폴더 생성
for s in SPLITS:
    os.makedirs(os.path.join(OUT_ROOT, s, "images"), exist_ok=True)
    os.makedirs(os.path.join(OUT_ROOT, s, "labels"), exist_ok=True)

# 1) 대상 파일 수집
class_files = defaultdict(list)
for lbl in os.listdir(LABEL_DIR):
    if not lbl.endswith(".txt"):       continue
    img = lbl.replace(".txt", ".jpg")
    img_path, lbl_path = os.path.join(IMAGE_DIR,img), os.path.join(LABEL_DIR,lbl)
    if not os.path.exists(img_path):   continue

    ids = {int(line.split()[0]) for line in open(lbl_path) if line.strip()}
    if not ids:                        continue

    for cid in ids:
        if cid in FIXED_COUNT:
            class_files[cid].append((img_path, lbl_path))
            break                      # 한 이미지가 여러 클래스 포함해도 첫 번째만

# 2) 클래스별 고정 개수만 무작위 선택 후 split
for cid, files in class_files.items():
    pick = random.sample(files, min(FIXED_COUNT[cid], len(files)))

    n_total = len(pick)
    n_train = floor(n_total * SPLITS["train"])
    n_valid = floor(n_total * SPLITS["valid"])
    # 나머지는 test
    split_map = (["train"]*n_train +
                 ["valid"]*n_valid +
                 ["test"] * (n_total - n_train - n_valid))
    random.shuffle(split_map)          # 이미지별 split 섞기

    for (img, lbl), split in zip(pick, split_map):
        dst_img = os.path.join(OUT_ROOT, split, "images", os.path.basename(img))
        dst_lbl = os.path.join(OUT_ROOT, split, "labels", os.path.basename(lbl))
        shutil.copy2(img, dst_img)
        shutil.copy2(lbl, dst_lbl)

print("✅ 클래스별 고정 수 추출 및 8:1:1 split 완료")
