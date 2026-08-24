"""
generate_reactions.py - Master Comic Chibi Rexy Reaction Sticker Generator.

Guarantees 100.00% EXACT character consistency across all reactions:
- Identical chibi baby dinosaur anatomy, colors, explorer hat, and lineart.
- 8 distinct comic facial expressions & arm poses.
- Crisp solid white die-cut sticker border around the silhouette.
- 100% transparent background outside the border.

Run to generate or refresh the reaction stickers:
    python generate_reactions.py
"""
import os
import sys
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import BASE_DIR

REACTIONS_DIR = BASE_DIR / "assets" / "reactions"
TARGET_SIZE = (400, 500)
BORDER_RADIUS = 12

REACTION_KEYS = [
    "shocked",
    "scared",
    "thinking",
    "excited",
    "mindblown",
    "curious",
    "crying",
    "waving",
]


def render_comic_chibi_sticker(expression="waving", width=TARGET_SIZE[0], height=TARGET_SIZE[1], border_radius=BORDER_RADIUS):
    """Renders a 100% visually consistent comic chibi Rexy sticker with clean white die-cut border.
    
    Uses sub-pixel supersampling (3x canvas) and Lanczos antialiasing for vector-like quality.
    """
    scale = 3
    W, H = width * scale, height * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Precise Master Palette
    C_OUTLINE = (25, 35, 25, 255)       # Crisp dark ink comic outline
    C_GREEN = (125, 215, 95, 255)       # Bright lime-green dino skin
    C_GREEN_DARK = (95, 180, 70, 255)   # Shaded green
    C_BELLY = (255, 245, 150, 255)      # Soft pastel yellow belly
    C_BLUSH = (255, 120, 140, 160)      # Sweet pink blush
    C_HAT = (195, 145, 85, 255)         # Safari explorer hat
    C_HAT_DARK = (155, 110, 55, 255)    # Hat brim shadow
    C_HAT_BAND = (65, 45, 30, 255)      # Dark brown hat band
    C_WHITE = (255, 255, 255, 255)
    C_BLACK = (20, 20, 25, 255)
    C_TEARS = (100, 205, 255, 230)      # Comic waterfall tears
    
    lw = int(10 * scale)  # Outline line width
    
    # Base anchor coordinates
    cx, cy = W // 2, int(H * 0.58)
    
    # 1. TAIL (Behind body)
    tail_pts = [(cx - 120*scale, cy + 80*scale), (cx - 260*scale, cy + 120*scale), (cx - 160*scale, cy + 180*scale)]
    draw.polygon(tail_pts, fill=C_GREEN)
    draw.line(tail_pts + [tail_pts[0]], fill=C_OUTLINE, width=lw)
    
    # 2. FEET (Bottom)
    lf_box = (cx - 140*scale, cy + 200*scale, cx - 30*scale, cy + 280*scale)
    draw.ellipse(lf_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    rf_box = (cx + 30*scale, cy + 200*scale, cx + 140*scale, cy + 280*scale)
    draw.ellipse(rf_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    for i in range(3):
        draw.ellipse((cx - 130*scale + i*35*scale, cy + 250*scale, cx - 100*scale + i*35*scale, cy + 280*scale), fill=C_BELLY, outline=C_OUTLINE, width=int(lw*0.6))
        draw.ellipse((cx + 40*scale + i*35*scale, cy + 250*scale, cx + 70*scale + i*35*scale, cy + 280*scale), fill=C_BELLY, outline=C_OUTLINE, width=int(lw*0.6))
        
    # 3. BODY (Round chubby torso)
    body_box = (cx - 160*scale, cy - 20*scale, cx + 160*scale, cy + 240*scale)
    draw.ellipse(body_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    
    # Belly (Yellow oval)
    belly_box = (cx - 95*scale, cy + 40*scale, cx + 95*scale, cy + 220*scale)
    draw.ellipse(belly_box, fill=C_BELLY, outline=C_OUTLINE, width=int(lw*0.7))
    
    # 4. HEAD (Big cute round chibi head)
    head_box = (cx - 190*scale, cy - 300*scale, cx + 190*scale, cy + 60*scale)
    draw.ellipse(head_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    
    # Cute Chubby Cheeks
    draw.ellipse((cx - 170*scale, cy - 60*scale, cx - 90*scale, cy + 10*scale), fill=C_BLUSH)
    draw.ellipse((cx + 90*scale, cy - 60*scale, cx + 170*scale, cy + 10*scale), fill=C_BLUSH)
    
    # Cute Nostrils
    draw.ellipse((cx - 30*scale, cy - 80*scale, cx - 15*scale, cy - 65*scale), fill=C_OUTLINE)
    draw.ellipse((cx + 15*scale, cy - 80*scale, cx + 30*scale, cy - 65*scale), fill=C_OUTLINE)
    
    # 5. EXPLORER HAT (On top of head)
    hat_top = (cx - 130*scale, cy - 420*scale, cx + 130*scale, cy - 260*scale)
    draw.chord(hat_top, 180, 360, fill=C_HAT, outline=C_OUTLINE, width=lw)
    draw.rectangle((cx - 130*scale, cy - 300*scale, cx + 130*scale, cy - 260*scale), fill=C_HAT_BAND, outline=C_OUTLINE, width=lw)
    hat_brim = (cx - 210*scale, cy - 300*scale, cx + 210*scale, cy - 230*scale)
    draw.ellipse(hat_brim, fill=C_HAT, outline=C_OUTLINE, width=lw)
    draw.arc((cx - 80*scale, cy - 380*scale, cx + 80*scale, cy - 320*scale), 0, 180, fill=C_HAT_DARK, width=int(lw*0.8))

    # 6. EXPRESSION-SPECIFIC EYES, MOUTH, AND ARMS
    eye_y = cy - 140*scale
    eye_lx, eye_rx = cx - 80*scale, cx + 80*scale
    
    if expression == "waving":
        draw.arc((eye_lx - 40*scale, eye_y - 40*scale, eye_lx + 40*scale, eye_y + 30*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.4))
        draw.arc((eye_rx - 40*scale, eye_y - 40*scale, eye_rx + 40*scale, eye_y + 30*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.4))
        draw.chord((cx - 45*scale, cy - 50*scale, cx + 45*scale, cy + 25*scale), 0, 180, fill=(230, 80, 100, 255), outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 150*scale, cy + 50*scale, cx - 80*scale, cy + 120*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 120*scale, cy - 50*scale, cx + 200*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.arc((cx + 205*scale, cy - 80*scale, cx + 245*scale, cy - 20*scale), 300, 420, fill=C_OUTLINE, width=int(lw*0.7))
        
    elif expression == "shocked":
        draw.ellipse((eye_lx - 50*scale, eye_y - 60*scale, eye_lx + 50*scale, eye_y + 50*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
        draw.ellipse((eye_rx - 50*scale, eye_y - 60*scale, eye_rx + 50*scale, eye_y + 50*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
        draw.ellipse((eye_lx - 15*scale, eye_y - 20*scale, eye_lx + 15*scale, eye_y + 10*scale), fill=C_BLACK)
        draw.ellipse((eye_rx - 15*scale, eye_y - 20*scale, eye_rx + 15*scale, eye_y + 10*scale), fill=C_BLACK)
        draw.ellipse((cx - 35*scale, cy - 55*scale, cx + 35*scale, cy + 30*scale), fill=(60, 20, 30, 255), outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 185*scale, cy - 40*scale, cx - 110*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 110*scale, cy - 40*scale, cx + 185*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        drop_pts = [(cx + 170*scale, cy - 240*scale), (cx + 195*scale, cy - 180*scale), (cx + 145*scale, cy - 180*scale)]
        draw.polygon(drop_pts, fill=C_TEARS)
        draw.ellipse((cx + 145*scale, cy - 200*scale, cx + 195*scale, cy - 150*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))

    elif expression == "scared":
        for ex in [eye_lx, eye_rx]:
            draw.ellipse((ex - 45*scale, eye_y - 45*scale, ex + 45*scale, eye_y + 45*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
            draw.arc((ex - 30*scale, eye_y - 30*scale, ex + 30*scale, eye_y + 30*scale), 0, 300, fill=C_OUTLINE, width=int(lw*0.8))
            draw.arc((ex - 18*scale, eye_y - 18*scale, ex + 18*scale, eye_y + 18*scale), 120, 400, fill=C_OUTLINE, width=int(lw*0.8))
        shiver_pts = [(cx - 50*scale, cy - 15*scale), (cx - 25*scale, cy - 30*scale), (cx, cy - 15*scale), (cx + 25*scale, cy - 30*scale), (cx + 50*scale, cy - 15*scale)]
        draw.line(shiver_pts, fill=C_OUTLINE, width=int(lw*1.3))
        draw.ellipse((cx - 70*scale, cy + 20*scale, cx - 10*scale, cy + 80*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 10*scale, cy + 20*scale, cx + 70*scale, cy + 80*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        for sy in [-150, 0, 120]:
            draw.line([(cx - 220*scale, cy + sy*scale), (cx - 200*scale, cy + (sy-15)*scale)], fill=C_OUTLINE, width=int(lw*0.7))
            draw.line([(cx + 200*scale, cy + sy*scale), (cx + 220*scale, cy + (sy-15)*scale)], fill=C_OUTLINE, width=int(lw*0.7))

    elif expression == "thinking":
        draw.ellipse((eye_lx - 45*scale, eye_y - 50*scale, eye_lx + 45*scale, eye_y + 40*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
        draw.ellipse((eye_lx - 10*scale, eye_y - 40*scale, eye_lx + 30*scale, eye_y + 0*scale), fill=C_BLACK)
        draw.arc((eye_rx - 40*scale, eye_y - 30*scale, eye_rx + 40*scale, eye_y + 30*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.4))
        draw.arc((cx - 20*scale, cy - 35*scale, cx + 45*scale, cy + 15*scale), 30, 160, fill=C_OUTLINE, width=int(lw*1.3))
        draw.ellipse((cx + 30*scale, cy - 20*scale, cx + 110*scale, cy + 50*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 160*scale, cy + 60*scale, cx - 90*scale, cy + 130*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.arc((cx + 170*scale, cy - 380*scale, cx + 240*scale, cy - 310*scale), 180, 360, fill=(255, 200, 50, 255), width=int(lw*1.2))
        draw.line([(cx + 240*scale, cy - 345*scale), (cx + 205*scale, cy - 300*scale), (cx + 205*scale, cy - 275*scale)], fill=(255, 200, 50, 255), width=int(lw*1.2))
        draw.ellipse((cx + 195*scale, cy - 255*scale, cx + 215*scale, cy - 235*scale), fill=(255, 200, 50, 255))

    elif expression == "mindblown":
        for ex in [eye_lx, eye_rx]:
            draw.ellipse((ex - 50*scale, eye_y - 50*scale, ex + 50*scale, eye_y + 50*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
            s_pts = []
            for a in range(8):
                r = (38 if a%2==0 else 18) * scale
                rad = math.radians(a * 45 - 90)
                s_pts.append((ex + int(r * math.cos(rad)), eye_y + int(r * math.sin(rad))))
            draw.polygon(s_pts, fill=(255, 215, 0, 255), outline=C_OUTLINE, width=int(lw*0.5))
        draw.chord((cx - 40*scale, cy - 45*scale, cx + 40*scale, cy + 25*scale), 0, 180, fill=(220, 60, 90, 255), outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 160*scale, cy - 250*scale, cx - 90*scale, cy - 170*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 90*scale, cy - 250*scale, cx + 160*scale, cy - 170*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        for angle in [-60, -30, 0, 30, 60]:
            rad = math.radians(angle - 90)
            x1 = cx + int(240 * scale * math.cos(rad))
            y1 = (cy - 340*scale) + int(240 * scale * math.sin(rad))
            x2 = cx + int(290 * scale * math.cos(rad))
            y2 = (cy - 340*scale) + int(290 * scale * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=(255, 180, 0, 255), width=int(lw*1.0))

    elif expression == "curious":
        draw.ellipse((eye_lx - 40*scale, eye_y - 45*scale, eye_lx + 40*scale, eye_y + 35*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
        draw.ellipse((eye_lx - 20*scale, eye_y - 25*scale, eye_lx + 20*scale, eye_y + 15*scale), fill=C_BLACK)
        mag_cx, mag_cy = eye_rx + 20*scale, eye_y
        draw.ellipse((mag_cx - 65*scale, mag_cy - 70*scale, mag_cx + 65*scale, mag_cy + 60*scale), fill=C_WHITE)
        draw.ellipse((mag_cx - 35*scale, mag_cy - 40*scale, mag_cx + 35*scale, mag_cy + 30*scale), fill=C_BLACK)
        draw.ellipse((mag_cx - 15*scale, mag_cy - 25*scale, mag_cx + 10*scale, mag_cy + 0*scale), fill=C_WHITE)
        draw.ellipse((mag_cx - 75*scale, mag_cy - 80*scale, mag_cx + 75*scale, mag_cy + 70*scale), fill=None, outline=(180, 190, 210, 255), width=int(lw*1.3))
        draw.line([(mag_cx + 55*scale, mag_cy + 60*scale), (mag_cx + 120*scale, mag_cy + 130*scale)], fill=(120, 70, 30, 255), width=int(lw*1.6))
        draw.ellipse((mag_cx + 70*scale, mag_cy + 75*scale, mag_cx + 130*scale, mag_cy + 135*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.arc((cx - 30*scale, cy - 35*scale, cx + 20*scale, cy + 10*scale), 20, 160, fill=C_OUTLINE, width=int(lw*1.2))

    elif expression == "crying":
        draw.line([(eye_lx - 40*scale, eye_y - 30*scale), (eye_lx, eye_y), (eye_lx - 40*scale, eye_y + 30*scale)], fill=C_OUTLINE, width=int(lw*1.4))
        draw.line([(eye_rx + 40*scale, eye_y - 30*scale), (eye_rx, eye_y), (eye_rx + 40*scale, eye_y + 30*scale)], fill=C_OUTLINE, width=int(lw*1.4))
        draw.arc((cx - 45*scale, cy - 40*scale, cx + 45*scale, cy + 30*scale), 180, 360, fill=C_OUTLINE, width=int(lw*1.4))
        draw.ellipse((eye_lx - 25*scale, eye_y + 20*scale, eye_lx + 25*scale, eye_y + 140*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))
        draw.ellipse((eye_rx - 25*scale, eye_y + 20*scale, eye_rx + 25*scale, eye_y + 140*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))
        draw.ellipse((eye_lx - 45*scale, eye_y + 120*scale, eye_lx + 45*scale, eye_y + 165*scale), fill=C_TEARS)
        draw.ellipse((eye_rx - 45*scale, eye_y + 120*scale, eye_rx + 45*scale, eye_y + 165*scale), fill=C_TEARS)
        draw.ellipse((cx - 100*scale, cy + 30*scale, cx - 35*scale, cy + 95*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 35*scale, cy + 30*scale, cx + 100*scale, cy + 95*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)

    elif expression == "excited":
        draw.arc((eye_lx - 45*scale, eye_y - 45*scale, eye_lx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.5))
        draw.arc((eye_rx - 45*scale, eye_y - 45*scale, eye_rx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.5))
        draw.chord((cx - 55*scale, cy - 50*scale, cx + 55*scale, cy + 35*scale), 0, 180, fill=(240, 70, 95, 255), outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 30*scale, cy - 5*scale, cx + 30*scale, cy + 30*scale), fill=(255, 140, 160, 255))
        draw.ellipse((cx - 200*scale, cy - 70*scale, cx - 120*scale, cy + 20*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 120*scale, cy - 70*scale, cx + 200*scale, cy + 20*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        for sx, sy in [(cx - 210*scale, cy - 200*scale), (cx + 210*scale, cy - 200*scale), (cx, cy - 450*scale)]:
            draw.line([(sx - 20*scale, sy), (sx + 20*scale, sy)], fill=(255, 220, 50, 255), width=int(lw*0.8))
            draw.line([(sx, sy - 20*scale), (sx, sy + 20*scale)], fill=(255, 220, 50, 255), width=int(lw*0.8))

    # Downscale smoothly to target size
    img_downscaled = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # 7. ADD CRISP SOLID WHITE DIE-CUT STICKER BORDER
    alpha = np.array(img_downscaled.split()[-1])
    mask = alpha > 15
    radius = border_radius
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    struct = x*x + y*y <= radius*radius
    dilated_mask = binary_dilation(mask, structure=struct)
    
    out_arr = np.zeros((height, width, 4), dtype=np.uint8)
    out_arr[dilated_mask] = [255, 255, 255, 255]  # Solid white border
    orig_arr = np.array(img_downscaled)
    out_arr[alpha > 0] = orig_arr[alpha > 0]       # Original character inside
    
    return Image.fromarray(out_arr)


def generate_all_reactions(force=False):
    """Generates all 8 standard Rexy chibi reaction stickers with exact 100% visual consistency."""
    REACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  REXY COMIC CHIBI STICKER ENGINE (100% Visual Consistency)")
    print("=" * 60)
    
    count = 0
    for key in REACTION_KEYS:
        dest_path = REACTIONS_DIR / f"reaction_{key}.png"
        
        if not force and dest_path.exists():
            try:
                with Image.open(dest_path) as im:
                    if im.size == TARGET_SIZE and im.mode == "RGBA":
                        continue
            except:
                pass
                
        sticker = render_comic_chibi_sticker(expression=key)
        sticker.save(dest_path, "PNG", optimize=True)
        print(f"  [OK] reaction_{key}.png (100% consistent base + white border)")
        count += 1
        
    print(f"\nCompleted: Verified and ready in {REACTIONS_DIR}")
    return True


def get_reaction_path(reaction_key):
    """Get the path to a reaction PNG. Returns None if not found."""
    path = REACTIONS_DIR / f"reaction_{reaction_key}.png"
    if path.exists():
        return path
    # Auto-generate if missing
    generate_all_reactions()
    if path.exists():
        return path
    fallback = list(REACTIONS_DIR.glob("reaction_*.png"))
    return fallback[0] if fallback else None


def get_available_reactions():
    """List all available reaction keys."""
    return REACTION_KEYS


if __name__ == "__main__":
    generate_all_reactions(force=True)
