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
    width, height = 750, 150
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Outer dark glassmorphism container
    draw.rounded_rectangle([0, 0, width, height], radius=35, fill=(18, 18, 24, 235), outline=(255, 40, 40, 255), width=4)
    
    # Inner Red "SUBSCRIBE" button pill on right
    btn_w = 340
    btn_x0 = width - btn_w - 20
    draw.rounded_rectangle([btn_x0, 20, width - 20, height - 20], radius=25, fill=(225, 20, 20, 255))
    
    # Fonts
    font_bold = get_best_font(52, preferred="impact")
    font_btn = get_best_font(44, preferred="impact")
    
    # Left channel prompt text: "JOIN US"
    text_left = "SUBSCRIBE"
    draw.text((45, (height - 60)//2), text_left, font=font_bold, fill=(255, 255, 255, 255))
    
    # Right pill text: "▶ SUB"
    text_sub = "▶ CLICK"
    try:
        bbox = draw.textbbox((0, 0), text_sub, font=font_btn)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text_sub, font=font_btn)
        
    btn_center_x = btn_x0 + (btn_w // 2)
    draw.text((btn_center_x - (tw // 2), (height - th) // 2 - 6), text_sub, font=font_btn, fill=(255, 255, 255, 255))
    
    img.save(filepath)

def generate_like_button(filepath):
    """Generates a modern Like & Bell Pill with big bold text."""
    print("Generating modern high-CTR like button...")
    width, height = 400, 140
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Modern Blue/Cyan Glow Pill
    draw.rounded_rectangle([0, 0, width, height], radius=30, fill=(0, 120, 255, 245), outline=(255, 255, 255, 220), width=4)
    
    font = get_best_font(52, preferred="impact")
    text = "LIKE 👍"
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        
    # Drop shadow + main text
    draw.text(((width - tw)//2 + 2, (height - th)//2 - 4), text, font=font, fill=(0, 40, 120, 255))
    draw.text(((width - tw)//2, (height - th)//2 - 6), text, font=font, fill=(255, 255, 255, 255))
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
    """Generates large, high-contrast, crystal-clear CTA banner."""
    print(f"Generating CTA text banner: {text}...")
    width, height = 920, 130
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Dark semi-transparent pill background with gold neon border
    draw.rounded_rectangle([0, 0, width, height], radius=30, fill=(12, 12, 18, 235), outline=(255, 215, 0, 255), width=5)
    
    font = get_best_font(48, preferred="impact")
        
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        
    # Drop shadow
    draw.text(((width - tw)//2 + 2, (height - th)//2 - 4), text, font=font, fill=(0, 0, 0, 255))
    # Crisp white main text
    draw.text(((width - tw)//2, (height - th)//2 - 6), text, font=font, fill=(255, 255, 255, 255))
    img.save(filepath)

def generate_cta_assets(assets_dir):
    os.makedirs(assets_dir, exist_ok=True)
    bell_path = os.path.join(assets_dir, "bell.wav")
    click_path = os.path.join(assets_dir, "click.wav")
    sub_path = os.path.join(assets_dir, "subscribe.png")
    like_path = os.path.join(assets_dir, "like.png")
    bell_icon_path = os.path.join(assets_dir, "bell_icon.png")
    
    generate_bell_sound(bell_path)
    generate_click_sound(click_path)
    generate_subscribe_button(sub_path)
    generate_like_button(like_path)
    generate_bell_icon(bell_icon_path)
    
    generate_cta_text_banner(os.path.join(assets_dir, "cta_text_facts.png"), "SUB FOR MORE WEIRD FACTS 🤯")
    generate_cta_text_banner(os.path.join(assets_dir, "cta_text_stoicism.png"), "SUB FOR DAILY STOIC WISDOM 🏛️")
        
if __name__ == "__main__":
    generate_cta_assets("assets")

