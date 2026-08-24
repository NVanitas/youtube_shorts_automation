"""
generate_reactions.py - Generates pre-made Rexy reaction PNG stickers with transparent backgrounds.

Uses a strictly consistent chibi base character prompt and rembg AI segmentation
to produce flawless transparent PNGs with matching aesthetic across all reactions.

Run this script ONCE to create or refresh the reaction bank in assets/reactions/.
These PNGs are reused across all future videos without regeneration.
"""
import os
import sys
import time
import random
from pathlib import Path
from PIL import Image

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import BASE_DIR
from utils import download_ai_image

# Unified Chibi Base Character Description (Identical across all reactions for 100% visual consistency)
CHARACTER_BASE_PROMPT = (
    "cute chibi baby dinosaur character, adorable baby green T-Rex mascot, "
    "light lime-green smooth skin with soft pale-yellow belly, "
    "big glossy round black eyes with cute white reflections, friendly cute face, "
    "wearing a small brown safari explorer hat with dark band, "
    "small chubby round body, tiny short arms, small feet, cute tail, "
    "smooth 3D cartoon vinyl toy render, Pixar 3D animation style, Disney chibi aesthetic, "
    "studio lighting with soft shadows, solid pure white background, "
    "full body standing pose, centered, isolated, 8k resolution"
)

# Reaction-specific pose and facial expression definitions
REACTION_DEFINITIONS = {
    "shocked": "both hands on cheeks, mouth wide open in a big O shape, huge round wide-open eyes, looking completely shocked and stunned, jaw dropped, hilarious cute reaction, facing camera",
    "scared": "shivering and trembling with fear, knees knocking together, teeth chattering, sweating drop on head, terrified cute wide-eyed expression, facing camera",
    "thinking": "one tiny arm tapping chin, looking upward and to the side with curious raised eyebrow, thoughtful inquisitive expression, facing camera",
    "excited": "jumping joyfully in the air with tiny arms raised high, huge happy open-mouth smile, eyes squinted in joy, sparkles, energetic cute celebration pose, facing camera",
    "mindblown": "eyes wide open with glowing star reflections, both hands holding head in utter disbelief and amazement, mouth wide open in awe, blown away expression, facing camera",
    "curious": "holding a vintage magnifying glass up to one eye, peering through the glass, leaning slightly forward, curious detective expression, facing camera",
    "crying": "crying with dramatic cartoon tears streaming down cheeks, sad pouty mouth, hands wiping eyes, dramatically sad cute expression, facing camera",
    "waving": "waving friendly with one tiny hand, other hand on hip, bright warm welcoming smile, happy friendly greeting pose, facing camera",
}

REACTIONS_DIR = BASE_DIR / "assets" / "reactions"
TARGET_SIZE = (400, 500)


def remove_background_ai(img):
    """Remove background using rembg deep learning model (U2-Net).
    
    Produces clean alpha matting with smooth anti-aliased edges regardless of background color.
    """
    try:
        import rembg
        return rembg.remove(img)
    except Exception as e:
        print(f"  [rembg fallback] Could not use rembg ({e}), using color flood fill...")
        # Fallback to white/light background removal
        img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            # If near white (R>240, G>240, B>240) make transparent
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img


def generate_single_reaction(reaction_key, reaction_desc, output_path, retries=3):
    """Generate a single reaction PNG with transparent background using the unified chibi prompt."""
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
            
            # Apply AI background removal
            transparent_img = remove_background_ai(raw_img)
            
            # Crop to content (remove empty transparent borders)
            bbox = transparent_img.getbbox()
            if bbox:
                # Add slight padding inside bbox if possible
                transparent_img = transparent_img.crop(bbox)
            
            # Resize to fit within target sticker size (maintaining aspect ratio)
            transparent_img.thumbnail((TARGET_SIZE[0] - 20, TARGET_SIZE[1] - 20), Image.Resampling.LANCZOS)
            
            # Center on target-sized canvas
            canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
            paste_x = (TARGET_SIZE[0] - transparent_img.width) // 2
            paste_y = (TARGET_SIZE[1] - transparent_img.height) // 2
            canvas.paste(transparent_img, (paste_x, paste_y), transparent_img)
            
            # Save as PNG with full alpha channel
            canvas.save(output_path, "PNG", optimize=True)
            
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            
            print(f"  [OK] {reaction_key}: saved to {output_path.name} ({canvas.size}, RGBA)")
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
    print("  REXY CHIBI REACTION BANK GENERATOR (rembg AI Pipeline)")
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
        
        print(f"\nGenerating reaction: '{key}'...")
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
