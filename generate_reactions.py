"""
generate_reactions.py - Generates cute comic chibi Rexy reaction PNG stickers with a clean white die-cut border.

Aesthetic Style:
- 2D/Cel-shaded Kawaii Comic Chibi Mascot
- Crisp comic ink outlines & vibrant pastel palette
- Cute blushing cheeks & expressive comic faces
- Isolated with rembg AI segmentation
- Clean solid white die-cut sticker border around the silhouette
- 100% transparent background outside the white border

Run with --force to regenerate all reactions:
    python generate_reactions.py --force
"""
import os
import sys
import time
import random
from pathlib import Path
from PIL import Image
import numpy as np
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

# Unified Comic Chibi Base Character Description (100% consistent across all reactions)
CHARACTER_BASE_PROMPT = (
    "kawaii cute baby green T-Rex dinosaur chibi mascot, super cute 2D comic cartoon sticker style, "
    "clean crisp dark comic ink outlines, cel-shaded vibrant pastel colors, adorable huge sparkly comic eyes, "
    "cute pink blush on chubby cheeks, wearing a small brown safari explorer hat with dark band, "
    "soft pale-yellow belly, tiny round chubby body, tiny short arms, small feet and tail, "
    "flat solid pure white background, cute comic sticker illustration, Japanese line sticker aesthetic, "
    "2D vector art style, high quality"
)

# Reaction-specific comic poses and facial expressions
REACTION_DEFINITIONS = {
    "shocked": "both hands on cheeks, mouth wide open in a dramatic comic O shape, huge wide-open starry shocked eyes, sweat drop on forehead, jaw dropped, dramatic funny comic shock reaction, facing camera",
    "scared": "shivering and trembling with fear, knees knocking together, teeth chattering, sweating cartoon drops, terrified cute wide-eyed expression with spiral eyes, funny scared comic pose, facing camera",
    "thinking": "one tiny arm tapping chin thoughtfully, other hand on hip, looking upward with a cute question mark above head, curious raised comic eyebrow, contemplative adorable expression, facing camera",
    "excited": "jumping joyfully in the air with tiny arms raised high, huge happy open-mouth smile, eyes squinted in cute happy arcs, sparkles and stars around, energetic kawaii celebration pose, facing camera",
    "mindblown": "eyes wide open with glowing starburst reflections, hands on head in utter comic disbelief, mouth wide open in awe, comic explosion lines around head, mind blown expression, facing camera",
    "curious": "holding a vintage magnifying glass up to one eye with an oversized curious eye, leaning slightly forward, cute detective magnifying glass pose, inquisitive expression, facing camera",
    "crying": "crying with dramatic comic waterfall tears streaming down cheeks, sad cute pouty mouth, tiny hands wiping eyes, dramatically sad adorable comic expression, facing camera",
    "waving": "waving friendly with one tiny hand, other hand on round tummy, bright warm welcoming smile, happy kawaii greeting pose, facing camera",
}

REACTIONS_DIR = BASE_DIR / "assets" / "reactions"
TARGET_SIZE = (400, 500)
BORDER_THICKNESS = 12  # White sticker die-cut border radius in pixels


def add_white_sticker_border(img_rgba, border_radius=BORDER_THICKNESS):
    """Adds a smooth, crisp, uniform solid white die-cut sticker outline around the character.
    
    Args:
        img_rgba (PIL.Image.Image): RGBA image with transparent background.
        border_radius (int): Pixel radius of the white outline border.
        
    Returns:
        PIL.Image.Image: RGBA image with the white sticker border and transparent background.
    """
    alpha = np.array(img_rgba.split()[-1])
    mask = alpha > 20
    
    # Generate circular structuring element for smooth rounded border
    radius = border_radius
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    struct = x*x + y*y <= radius*radius
    
    # Dilate mask outwards
    dilated_mask = binary_dilation(mask, structure=struct)
    
    # Create RGBA output canvas
    out_arr = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    
    # Fill dilated outline with solid white
    out_arr[dilated_mask] = [255, 255, 255, 255]
    
    # Paste original character on top
    orig_arr = np.array(img_rgba)
    fg_mask = alpha > 0
    out_arr[fg_mask] = orig_arr[fg_mask]
    
    return Image.fromarray(out_arr)


def remove_background_ai(img):
    """Remove background using rembg deep learning model (U2-Net)."""
    try:
        import rembg
        return rembg.remove(img)
    except Exception as e:
        print(f"  [rembg fallback] Could not use rembg ({e}), using color threshold...")
        img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img


def generate_single_reaction(reaction_key, reaction_desc, output_path, retries=3):
    """Generate a single reaction comic sticker with a clean white die-cut border."""
    prompt = f"{CHARACTER_BASE_PROMPT}, {reaction_desc}"
    
    temp_path = output_path.parent / f"_temp_{reaction_key}.jpg"
    
    for attempt in range(retries):
        try:
            result = download_ai_image(prompt, temp_path)
            if not result or not temp_path.exists():
                print(f"  Attempt {attempt+1}/{retries} failed for '{reaction_key}': No image returned")
                time.sleep(2)
                continue
            
            # Load raw AI image
            raw_img = Image.open(temp_path).convert("RGB")
            
            # 1. Apply AI background removal
            transparent_img = remove_background_ai(raw_img)
            
            # 2. Crop to content
            bbox = transparent_img.getbbox()
            if bbox:
                transparent_img = transparent_img.crop(bbox)
                
            # 3. Add clean white die-cut sticker border
            bordered_img = add_white_sticker_border(transparent_img, border_radius=BORDER_THICKNESS)
            
            # 4. Resize to fit inside target sticker canvas (leaving a small margin)
            max_w, max_h = TARGET_SIZE[0] - 24, TARGET_SIZE[1] - 24
            bordered_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            
            # 5. Center on target canvas (400x500 RGBA)
            canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
            paste_x = (TARGET_SIZE[0] - bordered_img.width) // 2
            paste_y = (TARGET_SIZE[1] - bordered_img.height) // 2
            canvas.paste(bordered_img, (paste_x, paste_y), bordered_img)
            
            # Save as PNG with full alpha channel
            canvas.save(output_path, "PNG", optimize=True)
            
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            
            print(f"  [OK] {reaction_key}: saved to {output_path.name} ({canvas.size}, comic chibi with white border)")
            return True
            
        except Exception as e:
            print(f"  Attempt {attempt+1}/{retries} failed for '{reaction_key}': {e}")
            time.sleep(2)
    
    # Clean up temp on failure
    if temp_path.exists():
        try:
            temp_path.unlink()
        except:
            pass
    
    return False


def generate_all_reactions(force=False):
    """Generate all reaction PNGs.
    
    Args:
        force (bool): If True, regenerates all reaction PNGs even if they already exist.
    """
    REACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  REXY KAWAII COMIC CHIBI STICKER GENERATOR")
    print("  Style: 2D Comic Chibi + White Die-Cut Border")
    print("=" * 60)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for key, desc in REACTION_DEFINITIONS.items():
        output_path = REACTIONS_DIR / f"reaction_{key}.png"
        
        if not force and output_path.exists():
            try:
                with Image.open(output_path) as img:
                    if img.mode == "RGBA" and img.size == TARGET_SIZE:
                        print(f"  [SKIP] reaction_{key}.png already exists and is valid")
                        skipped += 1
                        continue
            except:
                pass
        
        print(f"\nGenerating comic chibi sticker: '{key}'...")
        success = generate_single_reaction(key, desc, output_path)
        
        if success:
            generated += 1
        else:
            failed += 1
            print(f"  [FAIL] Could not generate '{key}' after all retries")
    
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {generated} generated, {skipped} skipped, {failed} failed")
    print(f"  Reactions directory: {REACTIONS_DIR}")
    print(f"{'=' * 60}")
    
    return failed == 0


def get_reaction_path(reaction_key):
    """Get the path to a pre-generated reaction PNG. Returns None if not found."""
    path = REACTIONS_DIR / f"reaction_{reaction_key}.png"
    if path.exists():
        return path
    fallback = list(REACTIONS_DIR.glob("reaction_*.png"))
    if fallback:
        return random.choice(fallback)
    return None


def get_available_reactions():
    """List all available reaction keys that have valid PNG files."""
    available = []
    for key in REACTION_DEFINITIONS:
        path = REACTIONS_DIR / f"reaction_{key}.png"
        if path.exists():
            available.append(key)
    return available


if __name__ == "__main__":
    force_run = "--force" in sys.argv or "-f" in sys.argv
    generate_all_reactions(force=force_run)
