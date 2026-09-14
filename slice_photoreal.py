import cv2
import numpy as np
import os
from PIL import Image

brain_dir = r'C:\Users\Pongo\.gemini\antigravity-ide\brain\56d9dbbb-cbe7-4ea4-9e12-d862b8e21d5a'
assets_dir = os.path.abspath('assets')
anim_dir = os.path.join(assets_dir, 'anim')
os.makedirs(anim_dir, exist_ok=True)

def slice_2x2_grid(filename, animal_name):
    img_path = os.path.join(brain_dir, filename)
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    
    # Chroma key magenta
    b, g, r = cv2.split(img)
    is_magenta = (r > 130) & (b > 130) & (g < 90)
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[is_magenta] = 0
    alpha = cv2.medianBlur(alpha, 3)
    
    rgba = cv2.merge([r, g, b, alpha])
    
    half_h = h // 2
    half_w = w // 2
    
    quads = [
        (0, half_h, 0, half_w),            # 0: top-left
        (0, half_h, half_w, w),            # 1: top-right
        (half_h, h, 0, half_w),            # 2: bottom-left
        (half_h, h, half_w, w)             # 3: bottom-right
    ]
    
    for i, (y0, y1, x0, x1) in enumerate(quads):
        quad = rgba[y0:y1, x0:x1].copy()
        
        # Keep only the largest connected component in this quadrant
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(quad[:, :, 3])
        if num_labels > 1:
            largest_idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            clean_mask = np.zeros_like(quad[:, :, 3])
            clean_mask[labels == largest_idx] = 255
            quad[:, :, 3] = clean_mask
            
        pts = cv2.findNonZero(quad[:, :, 3])
        if pts is not None:
            bx, by, bw, bh = cv2.boundingRect(pts)
            pad = 4
            qh, qw = quad.shape[:2]
            crop = quad[max(0, by-pad):min(qh, by+bh+pad), max(0, bx-pad):min(qw, bx+bw+pad)]
            out_p = os.path.join(anim_dir, f"{animal_name}_{i}.png")
            Image.fromarray(crop).save(out_p)
            print(f"Saved photorealistic {animal_name}_{i}.png: {crop.shape}")

print("Slicing Photorealistic Fox...")
slice_2x2_grid('real_fox_walk_1789014157874.jpg', 'rubah')

print("Slicing Photorealistic Mammoth...")
slice_2x2_grid('real_mammoth_walk_1789014178256.jpg', 'mammoth')
