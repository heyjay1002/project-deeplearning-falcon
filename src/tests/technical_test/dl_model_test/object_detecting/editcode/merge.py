import os
import shutil

source_root = r"C:\Users\Administrator\Downloads\newdataset"
target_root = r"C:\Users\Administrator\Downloads\merged_dataset\fine_tune_dataset"

splits = ['train', 'valid', 'test']
subdirs = ['images', 'labels']

for folder in os.listdir(source_root):
    folder_path = os.path.join(source_root, folder)
    if not os.path.isdir(folder_path):
        continue

    for split in splits:
        for sub in subdirs:
            src_dir = os.path.join(folder_path, split, sub)
            tgt_dir = os.path.join(target_root, split, sub)

            if not os.path.exists(src_dir):
                continue  # 해당 split-subdir이 없는 경우 건너뜀

            os.makedirs(tgt_dir, exist_ok=True)

            for file in os.listdir(src_dir):
                if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.txt')):
                    continue

                src_path = os.path.join(src_dir, file)
                prefix = folder + "_"
                filename = prefix + file
                tgt_path = os.path.join(tgt_dir, filename)

                shutil.copy2(src_path, tgt_path)

print("\n✅ 모든 데이터가 fine_tune_dataset에 병합되었습니다.")
