import cv2
import numpy as np
import os

anim_dir = os.path.abspath('assets/anim')

for animal in ['rubah', 'mammoth']:
    for i in range(4):
        p = os.path.join(anim_dir, f"{animal}_{i}.png")
        if not os.path.exists(p):
            continue
        img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        b, g, r, a = cv2.split(img)
        
        # Magenta fringe detection:
        # Magenta has high R and B relative to G: (R > G + 30) and (B > G + 30)
        is_magenta_fringe = (r.astype(int) > g.astype(int) + 25) & (b.astype(int) > g.astype(int) + 25) & (g < 140)
        a[is_magenta_fringe] = 0
        
        # Ground shadow at very bottom for mammoth:
        if animal == 'mammoth':
            # Purple shadow on ground below feet:
            shadow_mask = (r > 60) & (b > 60) & (g < 30)
            a[shadow_mask] = 0
            
        # Slight morphological erosion of alpha edge (1px) to eliminate boundary bleed
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        a = cv2.morphologyEx(a, cv2.MORPH_OPEN, kernel)
        
        # Re-crop bounding box
        pts = cv2.findNonZero(a)
        if pts is not None:
            bx, by, bw, bh = cv2.boundingRect(pts)
            pad = 2
            h, w = img.shape[:2]
            y0, y1 = max(0, by-pad), min(h, by+bh+pad)
            x0, x1 = max(0, bx-pad), min(w, bx+bw+pad)
            clean_rgba = cv2.merge([b, g, r, a])[y0:y1, x0:x1]
            cv2.imwrite(p, clean_rgba)
            print(f"Cleaned {animal}_{i}.png: {clean_rgba.shape}")

print("Defringing complete!")
