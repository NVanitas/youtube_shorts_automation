import os
import random
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from utils import download_ai_image
from config import NICHES

def draw_text_with_stroke(draw, text, position, font, fill_color="yellow", stroke_color="black", stroke_width=6):
    """Draws text with a thick high-contrast outline for max readability on mobile screens."""
    x, y = position
    # Draw outline
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_color)

def generate_thumbnail(niche_key, title, keywords, output_path):
    """Generates a high-CTR 1080x1920 vertical thumbnail with bold text overlays for YouTube Shorts."""
    print(f"\nGenerating high-CTR vertical thumbnail for '{title}'...")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    niche = NICHES[niche_key]
    primary_kw = keywords[0] if keywords else niche_key
    
    # Temp file for raw background image
    temp_bg_path = output_path.parent / "temp_thumb_bg.jpg"
    
    # 1. Download vertical background image matching primary keyword (pure scenic background)
    prompt_kw = f"dramatic cinematic vertical {primary_kw} hd dramatic lighting"
    download_ai_image(prompt_kw, temp_bg_path)
    
    try:
        img = Image.open(temp_bg_path).convert("RGBA")
        img = img.resize((1080, 1920), Image.Resampling.BILINEAR)
    except Exception as e:
        print(f"Error opening downloaded background: {e}. Creating fallback colored canvas.")
        img = Image.new("RGBA", (1080, 1920), (20, 20, 30, 255))
        
    # 2. Apply contrast and vignette darkening overlay
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.25) # Boost contrast by 25%
    
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Top and Bottom dark gradients for text readability
    for y in range(500):
        alpha = int(220 * (1 - y / 500))
        draw_overlay.line([(0, y), (1080, y)], fill=(0, 0, 0, alpha))
        
    for y in range(1400, 1920):
        alpha = int(220 * ((y - 1400) / 520))
        draw_overlay.line([(0, y), (1080, y)], fill=(0, 0, 0, alpha))
        
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Overlay character sticker on top layer for facts niche (placed above gradients)
    if niche_key == "facts":
        try:
            from generate_reactions import get_reaction_path
            rexy_path = get_reaction_path("mindblown") or get_reaction_path("shocked")
            if rexy_path and rexy_path.exists():
                rexy_img = Image.open(rexy_path).convert("RGBA")
                # Keep original 400x500 sticker aspect and place safely
                rexy_img = rexy_img.resize((420, 525), Image.Resampling.LANCZOS)
                # Position safely in bottom-left safe zone (x=60, y=1260)
                img.paste(rexy_img, (60, 1260), rexy_img)
                print(f"Added character sticker overlay to thumbnail on top layer ({rexy_path.name})")
        except Exception as ce:
            print(f"Notice: Could not overlay character on thumbnail: {ce}")
    draw = ImageDraw.Draw(img)
    
    # Draw vibrant high-CTR neon border
    border_color = (255, 0, 0, 255) if niche_key == "facts" else (255, 215, 0, 255) # Red for facts, Gold for stoicism
    draw.rectangle([10, 10, 1070, 1910], outline=border_color, width=16)
    
    # 3. Add bold, vibrant text overlay
    try:
        font_title = ImageFont.truetype("impact.ttf", 100)
        font_sub = ImageFont.truetype("arialbd.ttf", 65)
    except Exception:
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 90)
            font_sub = ImageFont.truetype("arialbd.ttf", 60)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            
    # Extract short 2-3 word hook phrase from title
    clean_title = re.sub(r'[^\w\s]', '', title).upper()
    words = clean_title.split()
    
    if len(words) >= 4:
        line1 = " ".join(words[:2])
        line2 = " ".join(words[2:5])
    else:
        line1 = " ".join(words[:2]) if len(words) >= 2 else clean_title
        line2 = "WAIT FOR IT..."
        
    highlight_color = "#FFFF00" if niche_key == "facts" else "#FFD700"
    
    # Draw Top Hook Badge
    badge_bg = (204, 0, 0, 240) if niche_key == "facts" else (180, 120, 0, 240)
    draw.rounded_rectangle([140, 180, 940, 310], radius=25, fill=badge_bg, outline="white", width=4)
    
    badge_text = "MIND BLOWN" if niche_key == "facts" else "UNSHAKEABLE"
    try:
        bbox = draw.textbbox((0, 0), badge_text, font=font_sub)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        bw, bh = 400, 50
    draw.text(((1080 - bw) // 2, 245 - bh // 2), badge_text, font=font_sub, fill="white")
    
    # Draw Main Title Text Lines in Center
    try:
        b1 = draw.textbbox((0, 0), line1, font=font_title)
        w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
    except Exception:
        w1, h1 = 600, 80
        
    draw_text_with_stroke(draw, line1, ((1080 - w1) // 2, 850), font_title, fill_color="white", stroke_color="black", stroke_width=10)
    
    try:
        b2 = draw.textbbox((0, 0), line2, font=font_title)
        w2, h2 = b2[2] - b2[0], b2[3] - b2[1]
    except Exception:
        w2, h2 = 600, 80
        
    draw_text_with_stroke(draw, line2, ((1080 - w2) // 2, 850 + h1 + 35), font_title, fill_color=highlight_color, stroke_color="black", stroke_width=10)
    
    # Convert to RGB and save
    final_img = img.convert("RGB")
    final_img.save(output_path, quality=95)
    
    if temp_bg_path.exists():
        try:
            temp_bg_path.unlink()
        except Exception:
            pass
            
    print(f"[THUMBNAIL GENERATED] High-CTR vertical thumbnail saved to: {output_path}")
    return output_path
