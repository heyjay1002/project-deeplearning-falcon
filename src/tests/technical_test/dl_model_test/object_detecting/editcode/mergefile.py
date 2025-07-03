import os
import shutil

source_base = r"C:\Users\Administrator\Downloads\newdataset"
output_images = os.path.join(source_base, "merged_dataset", "train", "images")
output_labels = os.path.join(source_base, "merged_dataset", "train", "labels")

os.makedirs(output_images, exist_ok=True)
os.makedirs(output_labels, exist_ok=True)

folders_to_merge = ["bird4", "bird5", "bird6", "bird7", "fod4", "fod5"]

count = 0
for folder in folders_to_merge:
    img_path = os.path.join(source_base, folder, "train", "images")
    lbl_path = os.path.join(source_base, folder, "train", "labels")
    
    for fname in os.listdir(img_path):
        name, ext = os.path.splitext(fname)
        new_name = f"{folder}_{name}{ext}"  # 충돌 방지를 위해 prefix 붙이기
        shutil.copy(os.path.join(img_path, fname), os.path.join(output_images, new_name))
    
    for fname in os.listdir(lbl_path):
        name, ext = os.path.splitext(fname)
        new_name = f"{folder}_{name}{ext}"
        shutil.copy(os.path.join(lbl_path, fname), os.path.join(output_labels, new_name))

print("✅ 통합 완료!")
