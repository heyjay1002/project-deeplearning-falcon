import os
import random
import shutil

# 기준 설정
TARGETS = {
    'fod3': {'class_id': '1', 'max_samples': 300},
    'person8': {'class_id': '2', 'max_samples': 600}
}

BASE_DIR = r"C:\Users\Administrator\Downloads\newdataset"

def reduce_samples(folder_name, class_id, max_keep):
    folder_path = os.path.join(BASE_DIR, folder_name, 'train')
    image_dir = os.path.join(folder_path, 'images')
    label_dir = os.path.join(folder_path, 'labels')

    if not os.path.exists(image_dir) or not os.path.exists(label_dir):
        print(f"❌ 경로 없음: {folder_path}")
        return

    matched_files = []
    
    # 클래스 ID 포함된 라벨파일 추출
    for label_file in os.listdir(label_dir):
        if not label_file.endswith('.txt'):
            continue
        label_path = os.path.join(label_dir, label_file)
        with open(label_path, 'r') as f:
            lines = f.readlines()
            if any(line.startswith(class_id + ' ') for line in lines):
                matched_files.append(os.path.splitext(label_file)[0])  # 확장자 제거된 이름

    print(f"\n📂 {folder_name} → 클래스 {class_id} 전체: {len(matched_files)}개 → {max_keep}개만 유지")

    # 삭제 대상 결정
    if len(matched_files) <= max_keep:
        print(f"🔹 삭제 없음 (이미 {max_keep}개 이하)")
        return

    to_delete = random.sample(matched_files, len(matched_files) - max_keep)

    # 삭제 수행
    for name in to_delete:
        img_path = os.path.join(image_dir, name + '.jpg')
        if not os.path.exists(img_path):
            img_path = os.path.join(image_dir, name + '.png')  # png fallback

        label_path = os.path.join(label_dir, name + '.txt')

        if os.path.exists(img_path):
            os.remove(img_path)
        if os.path.exists(label_path):
            os.remove(label_path)

    print(f"🗑️ 삭제 완료: {len(to_delete)}개\n")

# 실행
for folder, info in TARGETS.items():
    reduce_samples(folder, info['class_id'], info['max_samples'])

print("✅ 클래스 제한에 따른 샘플 제거 완료")
