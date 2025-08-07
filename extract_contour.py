import os
import numpy as np
import cv2
from PIL import Image

def extract_contour_from_image(image_path):
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    _, mask = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 가장 큰 외곽선만 사용
        contour = max(contours, key=cv2.contourArea)
        contour = contour.squeeze().tolist()
        if isinstance(contour[0], int):  # 단일 점만 있을 때
            contour = [contour]
        return contour
    return []

def process_folder(folder):
    for i in range(1, 9):
        img_path = os.path.join(folder, f"{i}_cut.png")
        contour_path = os.path.join(folder, f"{i}_contour.npy")
        if os.path.exists(img_path):
            contour = extract_contour_from_image(img_path)
            np.save(contour_path, np.array(contour, dtype=np.int32))
            print(f"Saved contour: {contour_path}")
        else:
            print(f"Not found: {img_path}")

if __name__ == "__main__":
    for folder in ["aglia", "anaxa"]:
        process_folder(folder)
    print("모든 외곽선 추출 및 저장 완료!")
