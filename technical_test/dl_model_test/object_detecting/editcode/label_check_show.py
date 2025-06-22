import os
import cv2
import numpy as np

# 경로
image_dir = '/home/mac/blender_image/images/'
label_dir = '/home/mac/blender_image/labels/'
output_dir = '/home/mac/blender_image/test_image/'

# 클래스 색상 (최대 20개 지원)
def get_color(idx):
    np.random.seed(idx)
    return tuple(int(x) for x in np.random.randint(0, 255, 3))

os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(image_dir):
    if not filename.endswith('.png'):
        continue

    image_path = os.path.join(image_dir, filename)
    label_path = os.path.join(label_dir, filename.replace('.png', '.txt'))
    output_path = os.path.join(output_dir, filename)

    if not os.path.exists(label_path):
        continue

    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    with open(label_path, 'r') as f:
        for line in f:
            parts = list(map(float, line.strip().split()))
            class_id = int(parts[0])
            coords = parts[1:]

            polygon = []
            for i in range(0, len(coords), 2):
                x = round(coords[i] * w)
                y = round((1 - coords[i + 1]) * h)  # Y축 뒤집기
                polygon.append([x, y])

            if len(polygon) >= 3:
                pts = np.array(polygon, np.int32).reshape((-1, 1, 2))
                color = get_color(class_id)
                # 내부 채우기
                cv2.fillPoly(img, [pts], color)
                # 외곽선
                cv2.polylines(img, [pts], isClosed=True, color=(255,255,255), thickness=1)
                # 중앙 좌표에 class ID 텍스트
                cx, cy = np.mean(pts[:, 0, 0]), np.mean(pts[:, 0, 1])
                cv2.putText(img, str(class_id), (int(cx), int(cy)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 0), 2)

    cv2.imwrite(output_path, img)
