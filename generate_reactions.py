"""
generate_reactions.py - Generates pre-made Rexy reaction PNG stickers with transparent backgrounds.

Run this script ONCE to create the reaction bank in assets/reactions/.
These PNGs are reused across all future videos without regeneration.
"""
import os
import sys
import time
import random
from pathlib import Path
from PIL import Image
import numpy as np

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import BASE_DIR
from utils import download_ai_image

# Reaction definitions: (filename_suffix, AI prompt description)
REACTION_DEFINITIONS = {
    "shocked": "looking extremely shocked with wide open mouth and huge round eyes, hands on cheeks",
    "scared": "trembling and sweating with a terrified expression, teeth chattering",
    "thinking": "rubbing chin with a tiny hand, looking upward with a thoughtful curious expression",
    "excited": "jumping in the air with arms raised, huge smile, eyes sparkling with joy",
    "mindblown": "head tilted back in total amazement, jaw dropped, stars around head",
    "curious": "holding a large magnifying glass and leaning forward with one eye squinting",
    "crying": "crying with big cartoon tears streaming down, sad pouty face",
    "waving": "smiling warmly and waving at the viewer with one hand, friendly pose",
}

CHARACTER_BASE_PROMPT = (
    "cute baby green T-Rex dinosaur cartoon character wearing a little brown explorer hat, "
    "full body, chibi style, sticker art, thick black outline, "
    "isolated on solid bright green background #00FF00, "
    "no shadows, no ground, clean vector edges, centered, "
    "3D cartoon render, disney pixar style"
)

REACTIONS_DIR = BASE_DIR / "assets" / "reactions"
TARGET_SIZE = (400, 500)


def chroma_key_green(img, tolerance=80):
    """Remove bright green (#00FF00) background from an image and replace with transparency.
    
    Uses numpy vectorized operations for speed.
    """
    img = img.convert("RGBA")
    data = np.array(img)
    
    # Target green: R=0, G=255, B=0
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    
    # Green-dominant mask: G is high, R and B are relatively low
    green_mask = (
        (g > 150) &
        (g > r + tolerance) &
        (g > b + tolerance)
    )
    
    # Also catch near-pure-green pixels
    pure_green_mask = (
        (g > 200) &
        (r < 100) &
        (b < 100)
    )
    
    combined_mask = green_mask | pure_green_mask
    
    # Set alpha to 0 for green pixels
    data[combined_mask, 3] = 0
    
    # Soften edges: for pixels adjacent to transparent ones, reduce alpha slightly
    try:
        from scipy.ndimage import binary_dilation
        edge_mask = binary_dilation(combined_mask, iterations=1) & ~combined_mask
        data[edge_mask, 3] = (data[edge_mask, 3] * 0.5).astype(np.uint8)
    except ImportError:
        pass  # scipy not available, skip edge softening
    
    return Image.fromarray(data)


def generate_single_reaction(reaction_key, reaction_desc, output_path, retries=3):
    """Generate a single reaction PNG with transparent background."""
    prompt = f"{CHARACTER_BASE_PROMPT}, {reaction_desc}"
    
    # Temp file for raw AI image
    temp_path = output_path.parent / f"_temp_{reaction_key}.jpg"
    
    for attempt in range(retries):
        try:
            result = download_ai_image(prompt, temp_path)
            if not result or not temp_path.exists():
                print(f"  Attempt {attempt+1}/{retries} failed for '{reaction_key}': No image returned")
                time.sleep(2)
                continue
            
            # Load and process with chroma key
            raw_img = Image.open(temp_path).convert("RGBA")
            
            # Apply chroma key to remove green background
            transparent_img = chroma_key_green(raw_img)
            
            # Crop to content (remove empty transparent borders)
            bbox = transparent_img.getbbox()
            if bbox:
                transparent_img = transparent_img.crop(bbox)
            
            # Resize to target sticker size, maintaining aspect ratio
            transparent_img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
            
            # Center on target-sized canvas
            canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
            paste_x = (TARGET_SIZE[0] - transparent_img.width) // 2
            paste_y = (TARGET_SIZE[1] - transparent_img.height) // 2
            canvas.paste(transparent_img, (paste_x, paste_y), transparent_img)
            
            # Save as PNG with full alpha
            canvas.save(output_path, "PNG")
            
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            
            print(f"  [OK] {reaction_key}: saved to {output_path.name} ({canvas.size})")
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


def generate_all_reactions():
    """Generate all reaction PNGs if they don't already exist."""
    REACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  REXY REACTION BANK GENERATOR")
    print("=" * 60)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for key, desc in REACTION_DEFINITIONS.items():
        output_path = REACTIONS_DIR / f"reaction_{key}.png"
        
        if output_path.exists():
            try:
                with Image.open(output_path) as img:
                    if img.mode == "RGBA" and img.size == TARGET_SIZE:
                        print(f"  [SKIP] reaction_{key}.png already exists and is valid")
                        skipped += 1
                        continue
            except:
                pass
        
        print(f"\nGenerating reaction: '{key}' ({desc[:50]}...)")
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
    generate_all_reactions()
