import wave
import struct
import math
import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _apply_reverb(audio, sample_rate=44100, delay_ms=80, feedback=0.3, mix=0.35):
    """Applies a simple delay-line reverb to a list of audio samples."""
    delay_samples = int(sample_rate * delay_ms / 1000)
    output = list(audio)  # copy
    for i in range(delay_samples, len(output)):
        output[i] += output[i - delay_samples] * feedback
    # Second tap for richness
    delay2 = int(delay_samples * 1.7)
    for i in range(delay2, len(output)):
        output[i] += output[i - delay2] * feedback * 0.4
    # Mix dry/wet
    result = []
    for dry, wet in zip(audio, output):
        result.append(dry * (1.0 - mix) + wet * mix)
    return result

def generate_sonar_hook(filepath, duration=1.2, sample_rate=44100):
    """Generates a deep, intriguing submarine sonar ping + sub-bass pulse for 0:00 video openings."""
    print("Generating 0:00 submarine sonar sound hook...")
    num_samples = int(duration * sample_rate)
    audio = []
    
    # Dual-tone sonar ping (880Hz + 1760Hz) with sub-bass boom (65Hz)
    for i in range(num_samples):
        t = i / sample_rate
        ping_env = math.exp(-3.5 * t) if t >= 0 else 0
        ping = (0.6 * math.sin(2 * math.pi * 880 * t) + 0.3 * math.sin(2 * math.pi * 1760 * t)) * ping_env
        
        sub_env = math.exp(-4.5 * t)
        sub = 0.5 * math.sin(2 * math.pi * 65 * t) * sub_env
        
        val = math.tanh(ping + sub)
        audio.append(val * 0.5)
        
    audio = _apply_reverb(audio, sample_rate, delay_ms=120, feedback=0.4, mix=0.35)
    
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in audio:
            sample = math.tanh(sample)
            int_sample = max(-32768, min(32767, int(sample * 32767)))
            wav_file.writeframesraw(struct.pack('<h', int_sample))

def generate_bell_sound(filepath, duration=1.0, sample_rate=44100):
    print("Generating UI notification bell sound...")
    num_samples = int(duration * sample_rate)
    audio = []
    
    # Modern UI notification "Ding" (Cleaner, higher pitch, fast decay)
    freqs = [1400, 2800] # Fundamental + 1st harmonic
    decays = [6.0, 12.0]  # Very fast decay so it doesn't linger
    amps = [0.8, 0.2]     # Mostly fundamental
    
    for i in range(num_samples):
        t = i / sample_rate
        val = 0
        for f, d, a in zip(freqs, decays, amps):
            env = math.exp(-d * t)
            val += a * env * math.sin(2 * math.pi * f * t)
            
        # master envelope (very fast attack)
        if t < 0.005:
            val *= (t / 0.005)
            
        # Soft limit
        val = math.tanh(val)
        audio.append(val * 0.4) # Lower internal master volume
    
    # Apply a tiny bit of reverb for UI presence, not a church hall
    audio = _apply_reverb(audio, sample_rate, delay_ms=40, feedback=0.15, mix=0.15)
        
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in audio:
            sample = math.tanh(sample)
            int_sample = max(-32768, min(32767, int(sample * 32767)))
            wav_file.writeframesraw(struct.pack('<h', int_sample))
            
def get_best_font(size, preferred="impact"):
    """Bulletproof font loader that searches Windows system fonts and fallbacks."""
    candidates = []
    if preferred == "impact":
        candidates = [
            r"C:\Windows\Fonts\impact.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            "impact.ttf",
            "arialbd.ttf"
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\impact.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            "arialbd.ttf",
            "arial.ttf"
        ]
        
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

def draw_rounded_rect(draw, xy, rad, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+rad, y0, x1-rad, y1], fill=fill)
    draw.rectangle([x0, y0+rad, x1, y1-rad], fill=fill)
    draw.pieslice([x0, y0, x0+rad*2, y0+rad*2], 180, 270, fill=fill)
    draw.pieslice([x1-rad*2, y0, x1, y0+rad*2], 270, 360, fill=fill)
    draw.pieslice([x0, y1-rad*2, x0+rad*2, y1], 90, 180, fill=fill)
    draw.pieslice([x1-rad*2, y1-rad*2, x1, y1], 0, 90, fill=fill)

def generate_subscribe_button(filepath):
    """Generates a modern, ultra-high-CTR YouTube Subscribe Widget with big readable typography."""
    print("Generating modern high-CTR subscribe button...")
    width, height = 800, 155
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Outer dark glassmorphism container with red neon glow border
    draw.rounded_rectangle([0, 0, width, height], radius=38,
                            fill=(14, 14, 22, 240), outline=(220, 30, 30, 255), width=5)
    
    # Inner Red "SUBSCRIBE" pill button on right side
    btn_w = 350
    btn_x0 = width - btn_w - 18
    draw.rounded_rectangle([btn_x0, 18, width - 18, height - 18], radius=26,
                            fill=(210, 20, 20, 255))
    # Highlight gloss at top of red button
    draw.rounded_rectangle([btn_x0 + 8, 18, width - 26, height // 2], radius=20,
                            fill=(255, 80, 80, 60))
    
    # Fonts
    font_label = get_best_font(54, preferred="impact")  # Left label
    font_btn   = get_best_font(46, preferred="impact")  # Button text
    
    # Left label: channel name / action
    text_left = "FOLLOW + SUBSCRIBE"
    # Measure to check width fits, downsize if needed
    try:
        bbl = draw.textbbox((0, 0), text_left, font=font_label)
        tlw = bbl[2] - bbl[0]
    except AttributeError:
        tlw, _ = draw.textsize(text_left, font=font_label)
    
    if tlw > btn_x0 - 30:
        font_label = get_best_font(40, preferred="impact")
    
    draw.text((24, (height - 58) // 2), text_left, font=font_label,
              fill=(255, 255, 255, 255))
    
    # Right pill text
    text_sub = "CLICK NOW !"
    try:
        bbs = draw.textbbox((0, 0), text_sub, font=font_btn)
        tw, th = bbs[2] - bbs[0], bbs[3] - bbs[1]
    except AttributeError:
        tw, th = draw.textsize(text_sub, font=font_btn)
    
    btn_cx = btn_x0 + btn_w // 2
    # Drop shadow
    draw.text((btn_cx - tw // 2 + 2, (height - th) // 2 - 4), text_sub,
              font=font_btn, fill=(100, 0, 0, 200))
    # Main bright text
    draw.text((btn_cx - tw // 2, (height - th) // 2 - 6), text_sub,
              font=font_btn, fill=(255, 255, 255, 255))
    
    img.save(filepath)

def generate_like_button(filepath):
    """Generates a modern Like Pill with big bold text — NO emoji (renders as square on Impact/Arial)."""
    print("Generating modern high-CTR like button...")
    width, height = 420, 140
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Deep blue pill with white glow border
    draw.rounded_rectangle([0, 0, width, height], radius=30,
                            fill=(0, 100, 230, 245), outline=(180, 220, 255, 200), width=4)
    # Gloss highlight
    draw.rounded_rectangle([10, 8, width - 10, height // 2], radius=22,
                            fill=(255, 255, 255, 30))
    
    font = get_best_font(56, preferred="impact")
    text = "LIKE  +  SHARE"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
    
    cx = (width - tw) // 2
    cy = (height - th) // 2 - 5
    # Shadow
    draw.text((cx + 2, cy + 3), text, font=font, fill=(0, 30, 100, 200))
    # Main text
    draw.text((cx, cy), text, font=font, fill=(255, 255, 255, 255))
    img.save(filepath)

def generate_click_sound(filepath, duration=1.0, active_duration=0.08, sample_rate=44100):
    print("Generating UI click/bloop sound...")
    num_samples = int(duration * sample_rate)
    audio = []
    
    for i in range(num_samples):
        t = i / sample_rate
        if t < active_duration:
            freq = 1500 - (1000 * (t / active_duration))
            val = math.sin(2 * math.pi * freq * t) * math.exp(-40.0 * t)
            bloop = math.sin(2 * math.pi * 600 * t) * math.exp(-25.0 * t) * 0.5
            audio.append((val + bloop) * 0.7)
        elif t < 0.25:
            bloop = math.sin(2 * math.pi * 600 * t) * math.exp(-15.0 * t) * 0.15
            audio.append(bloop)
        else:
            audio.append(0.0)
        
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in audio:
            int_sample = max(-32768, min(32767, int(sample * 32767)))
            wav_file.writeframesraw(struct.pack('<h', int_sample))

def generate_bell_icon(filepath):
    print("Generating bell icon...")
    width, height = 150, 150
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    fill = (255, 215, 0, 255) # Gold
    draw.pieslice([37, 15, 112, 90], 180, 360, fill=fill)
    draw.rectangle([37, 52, 112, 105], fill=fill)
    draw_rounded_rect(draw, (22, 105, 127, 127), 7, fill)
    draw.pieslice([60, 127, 90, 150], 0, 180, fill=fill)
    
    img.save(filepath)

def generate_cta_text_banner(filepath, text):
    """Generates large, high-contrast, crystal-clear CTA banner.
    
    Emojis are intentionally STRIPPED — TrueType fonts (Impact, Arial) render
    emoji codepoints as empty squares on Windows. The text is kept to clean
    ASCII uppercase for maximum sharpness and legibility.
    """
    import re
    # Strip all emoji / non-BMP characters that Impact can't render
    clean_text = re.sub(r'[^\x00-\xFF]', '', text).strip()
    print(f"Generating CTA text banner: {clean_text}...")
    
    width, height = 980, 130
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Vivid gradient-like pill: deep navy → dark, gold neon border
    draw.rounded_rectangle([0, 0, width, height], radius=32,
                            fill=(8, 12, 28, 240),
                            outline=(255, 200, 0, 255), width=5)
    # Inner accent strip on left
    draw.rounded_rectangle([0, 0, 12, height], radius=6, fill=(255, 60, 60, 255))
    
    font = get_best_font(50, preferred="impact")
    
    try:
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(clean_text, font=font)

    cy = (height - th) // 2 - 4
    cx = (width - tw) // 2 + 8  # slight right offset for left accent strip
    # Deep shadow for depth
    draw.text((cx + 3, cy + 3), clean_text, font=font, fill=(0, 0, 0, 200))
    # Crisp golden-white main text
    draw.text((cx, cy), clean_text, font=font, fill=(255, 248, 220, 255))
    img.save(filepath)

def generate_cta_assets(assets_dir):
    os.makedirs(assets_dir, exist_ok=True)
    bell_path = os.path.join(assets_dir, "bell.wav")
    click_path = os.path.join(assets_dir, "click.wav")
    sub_path = os.path.join(assets_dir, "subscribe.png")
    like_path = os.path.join(assets_dir, "like.png")
    bell_icon_path = os.path.join(assets_dir, "bell_icon.png")
    
    sonar_path = os.path.join(assets_dir, "sonar_hook.wav")
    
    generate_sonar_hook(sonar_path)
    generate_bell_sound(bell_path)
    generate_click_sound(click_path)
    generate_subscribe_button(sub_path)
    generate_like_button(like_path)
    generate_bell_icon(bell_icon_path)
    
    generate_cta_text_banner(os.path.join(assets_dir, "cta_text_facts.png"), "SUB FOR MORE WEIRD FACTS 🤯")
    generate_cta_text_banner(os.path.join(assets_dir, "cta_text_stoicism.png"), "SUB FOR DAILY STOIC WISDOM 🏛️")
        
if __name__ == "__main__":
    generate_cta_assets("assets")

