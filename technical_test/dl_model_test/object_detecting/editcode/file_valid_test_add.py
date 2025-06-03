import os, shutil, random, pathlib
from math import floor

ROOT = r"C:\Users\Administrator\Downloads\newdataset"   # ← 경로 맞게 수정
RATIO = 0.10                                            # 10 %

IMG_EXT = (".jpg", ".jpeg", ".png")                     # 허용 확장자

def ensure(p): pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def init_class_dirs(cls_path):
    """test / valid 폴더(및 images/labels) 없으면 만든다."""
    for split in ("valid", "test"):
        for sub in ("images", "labels"):
            ensure(os.path.join(cls_path, split, sub))

def list_train_images(cls_path):
    img_dir = os.path.join(cls_path, "train", "images")
    return [f for f in os.listdir(img_dir) if f.lower().endswith(IMG_EXT)]

def move_pair(cls_path, fname, src_split, dst_split):
    img_src = os.path.join(cls_path, src_split, "images", fname)
    lbl_src = os.path.join(cls_path, src_split, "labels", os.path.splitext(fname)[0] + ".txt")
    img_dst = os.path.join(cls_path, dst_split, "images", fname)
    lbl_dst = os.path.join(cls_path, dst_split, "labels", os.path.basename(lbl_src))
    shutil.move(img_src, img_dst)
    shutil.move(lbl_src, lbl_dst)

def process_class(cls_path):
    init_class_dirs(cls_path)
    imgs = list_train_images(cls_path)
    if not imgs:
        print(f"⚠️  {cls_path}  ─ train/images 가 비어 있음")
        return

    n = len(imgs)
    n_valid = floor(n * RATIO)
    n_test  = floor(n * RATIO)

    random.shuffle(imgs)
    valid_set = imgs[:n_valid]
    test_set  = imgs[n_valid:n_valid+n_test]

    for f in valid_set:
        move_pair(cls_path, f, "train", "valid")
    for f in test_set:
        move_pair(cls_path, f, "train", "test")

    print(f"✅ {os.path.basename(cls_path)}  ─ train {n} → "
          f"valid {len(valid_set)}, test {len(test_set)} 로 분할 완료")

def main():
    random.seed(42)                                      # 결과 재현용
    for cls in os.listdir(ROOT):
        cls_path = os.path.join(ROOT, cls)
        if os.path.isdir(cls_path) and os.path.isdir(os.path.join(cls_path, "train")):
            process_class(cls_path)

if __name__ == "__main__":
    main()
