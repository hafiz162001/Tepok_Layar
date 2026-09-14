import cv2
import numpy as np
import os
from PIL import Image

brain_dir = r'C:\Users\Pongo\.gemini\antigravity-ide\brain\56d9dbbb-cbe7-4ea4-9e12-d862b8e21d5a'
assets_dir = os.path.abspath('assets')
anim_dir = os.path.join(assets_dir, 'anim')
os.makedirs(anim_dir, exist_ok=True)

def process_sheet(filename, animal_name, n_frames):
    img_path = os.path.join(brain_dir, filename)
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    
    # Chroma key magenta: R > 140, B > 140, G < 90
    b, g, r = cv2.split(img)
    is_magenta = (r > 130) & (b > 130) & (g < 90)
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[is_magenta] = 0
    alpha = cv2.medianBlur(alpha, 3)
    
    rgba = cv2.merge([r, g, b, alpha])
    
    # Slice into n_frames along horizontal axis
    fw = w // n_frames
    for i in range(n_frames):
        sub = rgba[:, i*fw : (i+1)*fw]
        # Crop tight bounding box for the frame
        pts = cv2.findNonZero(sub[:, :, 3])
        if pts is not None:
            bx, by, bw, bh = cv2.boundingRect(pts)
            pad = 4
            y0, y1 = max(0, by - pad), min(h, by + bh + pad)
            x0, x1 = max(0, bx - pad), min(fw, bx + bw + pad)
            frame_crop = sub[y0:y1, x0:x1]
            out_p = os.path.join(anim_dir, f"{animal_name}_{i}.png")
            Image.fromarray(frame_crop).save(out_p)
            print(f"Saved {animal_name}_{i}.png: {frame_crop.shape}")

print("Processing Fox...")
process_sheet('fox_walk_cycle_1789013411911.jpg', 'rubah', 4)

print("Processing Mammoth...")
process_sheet('mammoth_walk_cycle_1789013433700.jpg', 'mammoth', 4)

print("Processing Spider...")
process_sheet('spider_crawl_cycle_1789013456323.jpg', 'laba_laba', 4)

print("Processing Mosquito...")
process_sheet('mosquito_flight_cycle_1789013475650.jpg', 'nyamuk', 3)
