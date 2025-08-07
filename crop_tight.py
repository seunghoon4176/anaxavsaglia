import os
from PIL import Image

def crop_to_content(image_path, save_path):
    img = Image.open(image_path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        cropped = img.crop(bbox)
        cropped.save(save_path)
        print(f"Saved: {save_path}")
    else:
        img.save(save_path)
        print(f"No content, saved original: {save_path}")

def process_folder(folder):
    for i in range(1, 9):
        src = os.path.join(folder, f"{i}.png")
        dst = os.path.join(folder, f"{i}_tight.png")
        if os.path.exists(src):
            crop_to_content(src, dst)
        else:
            print(f"Not found: {src}")

if __name__ == "__main__":
    for folder in ["aglia", "anaxa"]:
        process_folder(folder)
    print("모든 스프라이트를 딱 맞게 잘라 저장 완료!")
