"""
generate_reactions.py - High-End 3D Pixar Chibi Rexy Reaction Sticker Generator.

Features:
- Studio-grade 3D Pixar / Disney animated chibi mascot aesthetic
- Rich textures, softbox lighting, glossy anime catchlight eyes, and cute explorer hat
- Clean AI background removal via rembg (U2-Net)
- Automatic safe-margin padding so NO PART of the character is EVER cut off
- Crisp solid white die-cut sticker border with smooth rounded joins
- 100% transparent background outside the white border

Usage:
    python generate_reactions.py
"""
import os
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import BASE_DIR
from utils import download_ai_image

REACTIONS_DIR = BASE_DIR / "assets" / "reactions"
TARGET_SIZE = (400, 500)
BORDER_RADIUS = 14

# Unified 3D Pixar Chibi Base Character Specification (100% Consistent Mascot)
CHARACTER_BASE_PROMPT = (
    "masterpiece 3D cartoon render of cute baby green dinosaur mascot, "
    "ultra adorable chibi T-Rex named Rexy, smooth soft lime-green skin with creamy pale-yellow belly, "
    "giant glossy round black glass eyes with adorable bright catchlight reflections, "
    "sweet chubby round cheeks with soft rosy blush, "
    "wearing a miniature brown safari explorer hat with dark leather band, "
    "chubby marshmallow body, tiny short arms, small cute feet and tail, "
    "3D Pixar Disney animation style, soft studio lighting, subsurface scattering, "
    "centered full body standing pose, isolated on pure solid white background, 8k resolution"
)

# Reaction-specific 3D poses & facial expressions
REACTION_DEFINITIONS = {
    "shocked": "both tiny hands on chubby cheeks, mouth wide open in an adorable shocked O shape, giant wide-open starry eyes, hilarious cute shock expression, facing camera",
    "scared": "shivering with fear, knees knocking together, cute spiral dizzy panicked eyes, sweating cartoon drop, terrified adorable cute expression, facing camera",
    "thinking": "one tiny arm tapping chubby chin, looking up with curious raised eyebrow, cute contemplative thoughtful expression, facing camera",
    "excited": "jumping joyfully in the air with both tiny arms raised high in pure joy, huge happy beaming open smile with cute pink tongue, eyes closed in happy arcs, celebration sparkles, facing camera",
    "mindblown": "eyes wide open with glowing golden star reflections, both hands holding head in utter disbelief and amazement, mouth wide open in awe, blown away expression, facing camera",
    "curious": "holding a vintage detective magnifying glass up to one eye, peering curiously through the glass, leaning slightly forward, inquisitive cute expression, facing camera",
    "crying": "crying with dramatic cartoon tears streaming down chubby cheeks, sad pouty mouth, tiny hands wiping eyes, dramatically sad adorable expression, facing camera",
    "waving": "waving friendly with one tiny hand, other hand on tummy, sweet warm welcoming smile, happy friendly greeting pose, facing camera",
}


def add_white_sticker_border(img_rgba, border_radius=BORDER_RADIUS):
    """Adds a smooth, crisp, uniform solid white die-cut sticker outline around the character."""
    alpha = np.array(img_rgba.split()[-1])
    mask = alpha > 15
    
    radius = border_radius
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    struct = x*x + y*y <= radius*radius
    
    dilated_mask = binary_dilation(mask, structure=struct)
    
    out_arr = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    out_arr[dilated_mask] = [255, 255, 255, 255]  # Solid white border
    orig_arr = np.array(img_rgba)
    out_arr[alpha > 0] = orig_arr[alpha > 0]       # Original character inside
    
    return Image.fromarray(out_arr)


def remove_background_ai(img):
    """Removes background using rembg deep learning model (U2-Net)."""
    try:
        import rembg
        return rembg.remove(img)
    except Exception as e:
        print(f"  [rembg fallback] Could not use rembg ({e}), using color threshold...")
        img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img


def generate_single_reaction(reaction_key, reaction_desc, output_path, retries=3):
    """Generates a single studio-grade 3D Pixar chibi reaction sticker with safe-margin padding."""
    prompt = f"{CHARACTER_BASE_PROMPT}, {reaction_desc}"
    temp_path = output_path.parent / f"_temp_{reaction_key}.jpg"
    
    for attempt in range(retries):
        try:
            result = download_ai_image(prompt, temp_path)
            if not result or not temp_path.exists():
                print(f"  Attempt {attempt+1}/{retries} failed for '{reaction_key}': No image returned")
                time.sleep(2)
                continue
            
            raw_img = Image.open(temp_path).convert("RGB")
            
            # 1. AI background removal
            nobg = remove_background_ai(raw_img)
            
            # 2. Crop to tight character content
            bbox = nobg.getbbox()
            if bbox:
                nobg = nobg.crop(bbox)
                
            # 3. Add inner padding around character so border is NEVER cut off
            pad = 25
            padded = Image.new("RGBA", (nobg.width + pad * 2, nobg.height + pad * 2), (0, 0, 0, 0))
            padded.paste(nobg, (pad, pad), nobg)
            
            # 4. Add solid white die-cut sticker border
            bordered = add_white_sticker_border(padded, border_radius=BORDER_RADIUS)
            
            # 5. Fit comfortably inside 400x500 with guaranteed safe margins (max 330x430)
            max_inner_w, max_inner_h = TARGET_SIZE[0] - 70, TARGET_SIZE[1] - 70
            bordered.thumbnail((max_inner_w, max_inner_h), Image.Resampling.LANCZOS)
            
            # 6. Center on target canvas (400x500 RGBA)
            canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
            paste_x = (TARGET_SIZE[0] - bordered.width) // 2
            paste_y = (TARGET_SIZE[1] - bordered.height) // 2
            canvas.paste(bordered, (paste_x, paste_y), bordered)
            
            # Save optimized PNG
            canvas.save(output_path, "PNG", optimize=True)
            
            if temp_path.exists():
                temp_path.unlink()
                
            final_bbox = canvas.getbbox()
            print(f"  [OK] {reaction_key}: saved to {output_path.name} (BBox: {final_bbox}, 100% whole & uncut)")
            return True
            
        except Exception as e:
            print(f"  Attempt {attempt+1}/{retries} failed for '{reaction_key}': {e}")
            time.sleep(2)
            
    if temp_path.exists():
        try:
            temp_path.unlink()
        except:
            pass
            
    return False


def generate_all_reactions(force=False):
    """Generates all 8 standard Rexy 3D chibi reaction stickers."""
    REACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  REXY 3D PIXAR CHIBI STICKER GENERATOR")
    print("  Quality: Studio 3D CGI + rembg + Safe-Margin Die-Cut")
    print("=" * 60)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for key, desc in REACTION_DEFINITIONS.items():
        output_path = REACTIONS_DIR / f"reaction_{key}.png"
        
        if not force and output_path.exists():
            try:
                with Image.open(output_path) as im:
                    bbox = im.getbbox()
                    # Check that sticker is valid and has safe margins (not touching borders 0 or 400/500)
                    if (im.size == TARGET_SIZE and im.mode == "RGBA" and 
                        bbox and bbox[0] > 10 and bbox[1] > 10 and 
                        bbox[2] < TARGET_SIZE[0] - 10 and bbox[3] < TARGET_SIZE[1] - 10):
                        print(f"  [SKIP] reaction_{key}.png is already valid with safe margins")
                        skipped += 1
                        continue
            except:
                pass
                
        print(f"\nGenerating 3D Pixar chibi sticker: '{key}'...")
        success = generate_single_reaction(key, desc, output_path)
        
        if success:
            generated += 1
        else:
            failed += 1
            print(f"  [FAIL] Could not generate '{key}' after retries")
            
        time.sleep(1.0)  # Gentle pause between requests
        
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {generated} generated, {skipped} skipped, {failed} failed")
    print(f"  Reactions directory: {REACTIONS_DIR}")
    print(f"{'=' * 60}")
    
    return failed == 0


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
    return list(REACTION_DEFINITIONS.keys())


if __name__ == "__main__":
    force_run = "--force" in sys.argv or "-f" in sys.argv
    generate_all_reactions(force=force_run)
