"""
generate_reactions.py - Premium Kawaii Chibi Rexy Reaction Sticker Generator.

Design Specifications:
- True Kawaii / Sanrio / LINE Sticker Aesthetic
- Oversized chubby head with blushing cheeks (hatch marks) & shiny anime highlights
- Chubby marshmallow body with baby claws and curved tail with yellow tip
- Safari explorer hat with ribbon and 3D depth
- 100.00% EXACT character consistency across all 8 reactions
- Crisp solid white die-cut sticker border (12px) with smooth rounded joins
- 100% transparent background outside the white border

Usage:
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


def render_kawaii_chibi_sticker(expression="waving", width=TARGET_SIZE[0], height=TARGET_SIZE[1], border_radius=BORDER_RADIUS):
    """Renders a 100% visually consistent premium Kawaii Chibi Rexy sticker with clean white die-cut border.
    
    Uses 3x supersampling and Lanczos downscaling for vector-sharp antialiasing.
    """
    scale = 3
    W, H = width * scale, height * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Premium Kawaii Color Palette
    C_OUTLINE = (28, 38, 28, 255)       # Rich dark ink comic outline
    C_GREEN = (145, 225, 110, 255)      # Super bright cheerful lime green
    C_GREEN_SHADOW = (110, 195, 80, 255)# Soft cel shadow green
    C_BELLY = (255, 250, 165, 255)      # Soft creamy yellow belly
    C_BLUSH = (255, 130, 155, 180)      # Sweet kawaii pink blush
    C_HAT = (210, 160, 100, 255)        # Warm khaki explorer hat
    C_HAT_SHADOW = (175, 125, 70, 255)  # Hat shadow
    C_HAT_BAND = (75, 50, 35, 255)      # Dark brown hat band
    C_WHITE = (255, 255, 255, 255)
    C_BLACK = (25, 25, 30, 255)
    C_TEARS = (95, 210, 255, 230)       # Vivid aqua cartoon tears
    C_GOLD = (255, 215, 40, 255)        # Star/Gold sparkles
    C_MOUTH_INSIDE = (240, 75, 105, 255)# Bright cute pink mouth
    C_TONGUE = (255, 145, 170, 255)     # Cute pastel tongue
    
    lw = int(11 * scale)  # Bold sticker outline width
    
    # Center anchor
    cx, cy = W // 2, int(H * 0.58)
    
    # 1. TAIL (Curved cute chubby dino tail)
    tail_pts = [
        (cx - 100*scale, cy + 90*scale),
        (cx - 240*scale, cy + 110*scale),
        (cx - 260*scale, cy + 70*scale),
        (cx - 230*scale, cy + 50*scale),
        (cx - 130*scale, cy + 140*scale)
    ]
    draw.polygon(tail_pts, fill=C_GREEN)
    draw.line(tail_pts + [tail_pts[0]], fill=C_OUTLINE, width=lw, joint="round")
    # Tail tip (yellow accent)
    draw.ellipse((cx - 270*scale, cy + 50*scale, cx - 220*scale, cy + 100*scale), fill=C_BELLY, outline=C_OUTLINE, width=int(lw*0.7))
    
    # 2. CHUBBY FEET
    draw.ellipse((cx - 145*scale, cy + 195*scale, cx - 35*scale, cy + 285*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
    draw.ellipse((cx + 35*scale, cy + 195*scale, cx + 145*scale, cy + 285*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
    for i in range(3):
        draw.ellipse((cx - 135*scale + i*35*scale, cy + 250*scale, cx - 105*scale + i*35*scale, cy + 280*scale), fill=C_WHITE, outline=C_OUTLINE, width=int(lw*0.5))
        draw.ellipse((cx + 45*scale + i*35*scale, cy + 250*scale, cx + 75*scale + i*35*scale, cy + 280*scale), fill=C_WHITE, outline=C_OUTLINE, width=int(lw*0.5))
        
    # 3. CHUBBY MARSHMALLOW BODY
    body_box = (cx - 165*scale, cy - 15*scale, cx + 165*scale, cy + 245*scale)
    draw.ellipse(body_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    
    # Soft Yellow Belly
    belly_box = (cx - 100*scale, cy + 45*scale, cx + 100*scale, cy + 225*scale)
    draw.ellipse(belly_box, fill=C_BELLY, outline=C_OUTLINE, width=int(lw*0.6))
    
    # 4. OVERSIZED ULTRA-CUTE CHIBI HEAD
    head_box = (cx - 195*scale, cy - 305*scale, cx + 195*scale, cy + 65*scale)
    draw.ellipse(head_box, fill=C_GREEN, outline=C_OUTLINE, width=lw)
    
    # Rosy Blushing Cheeks (with kawaii hatch marks)
    draw.ellipse((cx - 175*scale, cy - 65*scale, cx - 85*scale, cy + 15*scale), fill=C_BLUSH)
    draw.ellipse((cx + 85*scale, cy - 65*scale, cx + 175*scale, cy + 15*scale), fill=C_BLUSH)
    for offset in [-140, -115, 115, 140]:
        draw.line([(cx + offset*scale, cy - 35*scale), (cx + (offset+12)*scale, cy - 10*scale)], fill=(230, 80, 110, 200), width=int(lw*0.5))
    
    # Cute little snout & nostrils
    draw.ellipse((cx - 28*scale, cy - 80*scale, cx - 14*scale, cy - 66*scale), fill=C_OUTLINE)
    draw.ellipse((cx + 14*scale, cy - 80*scale, cx + 28*scale, cy - 66*scale), fill=C_OUTLINE)
    
    # 5. CUTE EXPLORER SAFARI HAT
    hat_top = (cx - 135*scale, cy - 425*scale, cx + 135*scale, cy - 265*scale)
    draw.chord(hat_top, 180, 360, fill=C_HAT, outline=C_OUTLINE, width=lw)
    draw.arc((cx - 75*scale, cy - 390*scale, cx + 75*scale, cy - 330*scale), 0, 180, fill=C_HAT_SHADOW, width=int(lw*0.7))
    draw.rectangle((cx - 135*scale, cy - 305*scale, cx + 135*scale, cy - 265*scale), fill=C_HAT_BAND, outline=C_OUTLINE, width=lw)
    hat_brim = (cx - 215*scale, cy - 305*scale, cx + 215*scale, cy - 235*scale)
    draw.ellipse(hat_brim, fill=C_HAT, outline=C_OUTLINE, width=lw)

    # 6. DYNAMIC KAWAII FACIAL EXPRESSIONS & ARMS
    eye_y = cy - 145*scale
    eye_lx, eye_rx = cx - 80*scale, cx + 80*scale
    
    def draw_sparkle(x, y, sz=25):
        s = sz * scale
        pts = [(x, y-s), (x+s*0.3, y-s*0.3), (x+s, y), (x+s*0.3, y+s*0.3), (x, y+s), (x-s*0.3, y+s*0.3), (x-s, y), (x-s*0.3, y-s*0.3)]
        draw.polygon(pts, fill=C_GOLD, outline=C_OUTLINE, width=int(lw*0.4))
    
    def draw_kawaii_eye(ex, ey, r=46, look_up=False):
        draw.ellipse((ex - r*scale, ey - r*scale, ex + r*scale, ey + r*scale), fill=C_BLACK, outline=C_OUTLINE, width=int(lw*0.8))
        hy = (ey - int(r*0.35)*scale) if not look_up else (ey - int(r*0.5)*scale)
        hx = ex - int(r*0.25)*scale
        draw.ellipse((hx - int(r*0.35)*scale, hy - int(r*0.35)*scale, hx + int(r*0.35)*scale, hy + int(r*0.35)*scale), fill=C_WHITE)
        draw.ellipse((ex + int(r*0.25)*scale, ey + int(r*0.25)*scale, ex + int(r*0.45)*scale, ey + int(r*0.45)*scale), fill=C_WHITE)
        draw.arc((ex - int(r*0.7)*scale, ey - int(r*0.7)*scale, ex + int(r*0.7)*scale, ey + int(r*0.7)*scale), 40, 140, fill=(160, 240, 130, 255), width=int(lw*0.5))

    if expression == "waving":
        draw.arc((eye_lx - 45*scale, eye_y - 45*scale, eye_lx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.5))
        draw.arc((eye_rx - 45*scale, eye_y - 45*scale, eye_rx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.5))
        draw.chord((cx - 45*scale, cy - 50*scale, cx + 45*scale, cy + 25*scale), 0, 180, fill=C_MOUTH_INSIDE, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 25*scale, cy - 10*scale, cx + 25*scale, cy + 22*scale), fill=C_TONGUE)
        draw.ellipse((cx - 150*scale, cy + 50*scale, cx - 80*scale, cy + 120*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 120*scale, cy - 50*scale, cx + 200*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw_sparkle(cx + 220*scale, cy - 60*scale, 20)
        draw_sparkle(cx + 180*scale, cy - 110*scale, 14)
        
    elif expression == "shocked":
        draw_kawaii_eye(eye_lx, eye_y, r=50)
        draw_kawaii_eye(eye_rx, eye_y, r=50)
        draw.ellipse((cx - 35*scale, cy - 55*scale, cx + 35*scale, cy + 30*scale), fill=C_MOUTH_INSIDE, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 20*scale, cy + 5*scale, cx + 20*scale, cy + 25*scale), fill=C_TONGUE)
        draw.ellipse((cx - 185*scale, cy - 40*scale, cx - 110*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 110*scale, cy - 40*scale, cx + 185*scale, cy + 40*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        drop_pts = [(cx + 175*scale, cy - 245*scale), (cx + 200*scale, cy - 185*scale), (cx + 150*scale, cy - 185*scale)]
        draw.polygon(drop_pts, fill=C_TEARS)
        draw.ellipse((cx + 150*scale, cy - 205*scale, cx + 200*scale, cy - 155*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))
        draw.ellipse((cx + 160*scale, cy - 195*scale, cx + 175*scale, cy - 175*scale), fill=C_WHITE)

    elif expression == "scared":
        for ex in [eye_lx, eye_rx]:
            draw.ellipse((ex - 46*scale, eye_y - 46*scale, ex + 46*scale, eye_y + 46*scale), fill=C_WHITE, outline=C_OUTLINE, width=lw)
            draw.arc((ex - 32*scale, eye_y - 32*scale, ex + 32*scale, eye_y + 32*scale), 0, 300, fill=C_OUTLINE, width=int(lw*0.9))
            draw.arc((ex - 20*scale, eye_y - 20*scale, ex + 20*scale, eye_y + 20*scale), 120, 420, fill=C_OUTLINE, width=int(lw*0.9))
        shiver_pts = [(cx - 50*scale, cy - 15*scale), (cx - 25*scale, cy - 30*scale), (cx, cy - 15*scale), (cx + 25*scale, cy - 30*scale), (cx + 50*scale, cy - 15*scale)]
        draw.line(shiver_pts, fill=C_OUTLINE, width=int(lw*1.3), joint="round")
        draw.ellipse((cx - 70*scale, cy + 20*scale, cx - 10*scale, cy + 80*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 10*scale, cy + 20*scale, cx + 70*scale, cy + 80*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        for sy in [-130, 10, 130]:
            draw.line([(cx - 225*scale, cy + sy*scale), (cx - 205*scale, cy + (sy-15)*scale)], fill=C_OUTLINE, width=int(lw*0.7))
            draw.line([(cx + 205*scale, cy + sy*scale), (cx + 225*scale, cy + (sy-15)*scale)], fill=C_OUTLINE, width=int(lw*0.7))

    elif expression == "thinking":
        draw_kawaii_eye(eye_lx, eye_y, r=46, look_up=True)
        draw.arc((eye_rx - 40*scale, eye_y - 30*scale, eye_rx + 40*scale, eye_y + 30*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.5))
        draw.arc((cx - 20*scale, cy - 35*scale, cx + 45*scale, cy + 15*scale), 30, 160, fill=C_OUTLINE, width=int(lw*1.4))
        draw.ellipse((cx + 30*scale, cy - 20*scale, cx + 110*scale, cy + 50*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 160*scale, cy + 60*scale, cx - 90*scale, cy + 130*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.arc((cx + 170*scale, cy - 380*scale, cx + 240*scale, cy - 310*scale), 180, 360, fill=C_GOLD, width=int(lw*1.3))
        draw.line([(cx + 240*scale, cy - 345*scale), (cx + 205*scale, cy - 300*scale), (cx + 205*scale, cy - 275*scale)], fill=C_GOLD, width=int(lw*1.3))
        draw.ellipse((cx + 195*scale, cy - 255*scale, cx + 215*scale, cy - 235*scale), fill=C_GOLD)

    elif expression == "mindblown":
        for ex in [eye_lx, eye_rx]:
            draw.ellipse((ex - 50*scale, eye_y - 50*scale, ex + 50*scale, eye_y + 50*scale), fill=C_BLACK, outline=C_OUTLINE, width=lw)
            draw_sparkle(ex, eye_y, 40)
        draw.chord((cx - 40*scale, cy - 45*scale, cx + 40*scale, cy + 25*scale), 0, 180, fill=C_MOUTH_INSIDE, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 20*scale, cy - 5*scale, cx + 20*scale, cy + 20*scale), fill=C_TONGUE)
        draw.ellipse((cx - 165*scale, cy - 255*scale, cx - 95*scale, cy - 175*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 95*scale, cy - 255*scale, cx + 165*scale, cy - 175*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        for angle in [-65, -35, 0, 35, 65]:
            rad = math.radians(angle - 90)
            x1 = cx + int(245 * scale * math.cos(rad))
            y1 = (cy - 340*scale) + int(245 * scale * math.sin(rad))
            x2 = cx + int(295 * scale * math.cos(rad))
            y2 = (cy - 340*scale) + int(295 * scale * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=C_GOLD, width=int(lw*1.1))

    elif expression == "curious":
        draw_kawaii_eye(eye_lx, eye_y, r=44)
        mag_cx, mag_cy = eye_rx + 20*scale, eye_y
        draw_kawaii_eye(mag_cx, mag_cy, r=68)
        draw.ellipse((mag_cx - 76*scale, mag_cy - 76*scale, mag_cx + 76*scale, mag_cy + 76*scale), fill=None, outline=(190, 205, 225, 255), width=int(lw*1.4))
        draw.arc((mag_cx - 65*scale, mag_cy - 65*scale, mag_cx + 65*scale, mag_cy + 65*scale), 200, 270, fill=C_WHITE, width=int(lw*0.8))
        draw.line([(mag_cx + 55*scale, mag_cy + 55*scale), (mag_cx + 120*scale, mag_cy + 125*scale)], fill=(130, 80, 40, 255), width=int(lw*1.6))
        draw.ellipse((mag_cx + 70*scale, mag_cy + 70*scale, mag_cx + 130*scale, mag_cy + 130*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.arc((cx - 30*scale, cy - 35*scale, cx + 20*scale, cy + 10*scale), 20, 160, fill=C_OUTLINE, width=int(lw*1.3))

    elif expression == "crying":
        draw.line([(eye_lx - 40*scale, eye_y - 25*scale), (eye_lx, eye_y), (eye_lx - 40*scale, eye_y + 25*scale)], fill=C_OUTLINE, width=int(lw*1.5), joint="round")
        draw.line([(eye_rx + 40*scale, eye_y - 25*scale), (eye_rx, eye_y), (eye_rx + 40*scale, eye_y + 25*scale)], fill=C_OUTLINE, width=int(lw*1.5), joint="round")
        draw.arc((cx - 45*scale, cy - 40*scale, cx + 45*scale, cy + 30*scale), 180, 360, fill=C_MOUTH_INSIDE, width=lw)
        draw.ellipse((eye_lx - 25*scale, eye_y + 20*scale, eye_lx + 25*scale, eye_y + 145*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))
        draw.ellipse((eye_rx - 25*scale, eye_y + 20*scale, eye_rx + 25*scale, eye_y + 145*scale), fill=C_TEARS, outline=C_OUTLINE, width=int(lw*0.7))
        draw.ellipse((eye_lx - 45*scale, eye_y + 125*scale, eye_lx + 45*scale, eye_y + 170*scale), fill=C_TEARS)
        draw.ellipse((eye_rx - 45*scale, eye_y + 125*scale, eye_rx + 45*scale, eye_y + 170*scale), fill=C_TEARS)
        draw.ellipse((cx - 100*scale, cy + 30*scale, cx - 35*scale, cy + 95*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 35*scale, cy + 30*scale, cx + 100*scale, cy + 95*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)

    elif expression == "excited":
        draw.arc((eye_lx - 45*scale, eye_y - 45*scale, eye_lx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.6))
        draw.arc((eye_rx - 45*scale, eye_y - 45*scale, eye_rx + 45*scale, eye_y + 25*scale), 200, 340, fill=C_OUTLINE, width=int(lw*1.6))
        draw.chord((cx - 55*scale, cy - 50*scale, cx + 55*scale, cy + 35*scale), 0, 180, fill=C_MOUTH_INSIDE, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx - 30*scale, cy - 5*scale, cx + 30*scale, cy + 30*scale), fill=C_TONGUE)
        draw.ellipse((cx - 200*scale, cy - 70*scale, cx - 120*scale, cy + 20*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw.ellipse((cx + 120*scale, cy - 70*scale, cx + 200*scale, cy + 20*scale), fill=C_GREEN, outline=C_OUTLINE, width=lw)
        draw_sparkle(cx - 210*scale, cy - 200*scale, 22)
        draw_sparkle(cx + 210*scale, cy - 200*scale, 22)
        draw_sparkle(cx, cy - 455*scale, 26)

    # Downscale with Lanczos for smooth sub-pixel antialiasing
    img_downscaled = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # 7. ADD CRISP SOLID WHITE DIE-CUT STICKER BORDER
    alpha = np.array(img_downscaled.split()[-1])
    mask = alpha > 15
    radius = border_radius
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    struct = x*x + y*y <= radius*radius
    dilated_mask = binary_dilation(mask, structure=struct)
    
    out_arr = np.zeros((height, width, 4), dtype=np.uint8)
    out_arr[dilated_mask] = [255, 255, 255, 255]
    orig_arr = np.array(img_downscaled)
    out_arr[alpha > 0] = orig_arr[alpha > 0]
    
    return Image.fromarray(out_arr)


def generate_all_reactions(force=False):
    """Generates all 8 standard Rexy chibi reaction stickers with exact 100% visual consistency."""
    REACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  REXY KAWAII CHIBI STICKER ENGINE (100% Visual Consistency)")
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
                
        sticker = render_kawaii_chibi_sticker(expression=key)
        sticker.save(dest_path, "PNG", optimize=True)
        print(f"  [OK] reaction_{key}.png (Kawaii sticker with white die-cut border)")
        count += 1
        
    print(f"\nCompleted: Verified and ready in {REACTIONS_DIR}")
    return True


def get_reaction_path(reaction_key):
    """Get the path to a reaction PNG. Returns None if not found."""
    path = REACTIONS_DIR / f"reaction_{reaction_key}.png"
    if path.exists():
        return path
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
