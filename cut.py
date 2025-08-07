import os
from PIL import Image

def auto_crop_sprite(image_path, save_path):
    img = Image.open(image_path).convert("RGBA")
    bbox = img.getbbox()  # 투명하지 않은 영역의 bounding box
    if bbox:
        cropped = img.crop(bbox)
        cropped.save(save_path)
    else:
        img.save(save_path)  # 만약 완전히 투명하면 원본 저장

def process_folder(folder):
    for i in range(1, 9):
        src = os.path.join(folder, f"{i}.png")
        dst = os.path.join(folder, f"{i}_cut.png")
        if os.path.exists(src):
            auto_crop_sprite(src, dst)
            print(f"Cropped: {src} -> {dst}")
        else:
            print(f"Not found: {src}")

if __name__ == "__main__":
    for folder in ["aglia", "anaxa"]:
        process_folder(folder)
    print("모든 스프라이트 크롭 완료!")
