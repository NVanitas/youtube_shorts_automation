import wave
import struct
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont

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
            
def draw_rounded_rect(draw, xy, rad, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+rad, y0, x1-rad, y1], fill=fill)
    draw.rectangle([x0, y0+rad, x1, y1-rad], fill=fill)
    draw.pieslice([x0, y0, x0+rad*2, y0+rad*2], 180, 270, fill=fill)
    draw.pieslice([x1-rad*2, y0, x1, y0+rad*2], 270, 360, fill=fill)
    draw.pieslice([x0, y1-rad*2, x0+rad*2, y1], 90, 180, fill=fill)
    draw.pieslice([x1-rad*2, y1-rad*2, x1, y1], 0, 90, fill=fill)

def generate_subscribe_button(filepath):
    print("Generating subscribe button...")
    width, height = 600, 150
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Draw Red rounded rect
    draw_rounded_rect(draw, (0, 0, width, height), 30, (204, 0, 0, 255))
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 75)
    except:
        font = ImageFont.load_default()
        
    text = "SUBSCRIBE"
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        
    draw.text(((width - tw)//2, (height - th)//2 - 12), text, font=font, fill="white")
    img.save(filepath)

def generate_like_button(filepath):
    print("Generating like button...")
    width, height = 300, 150
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Draw Blue rounded rect for LIKE
    draw_rounded_rect(draw, (0, 0, width, height), 30, (0, 122, 255, 255))
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 75)
    except:
        font = ImageFont.load_default()
        
    text = "LIKE"
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        
    draw.text(((width - tw)//2, (height - th)//2 - 12), text, font=font, fill="white")
    img.save(filepath)

def generate_click_sound(filepath, duration=1.0, active_duration=0.08, sample_rate=44100):
    print("Generating UI click/bloop sound...")
    num_samples = int(duration * sample_rate)
    audio = []
    
    for i in range(num_samples):
        t = i / sample_rate
        if t < active_duration:
            # Layer 1: Quick frequency sweep (the 'click')
            freq = 1500 - (1000 * (t / active_duration))
            val = math.sin(2 * math.pi * freq * t)
            env = math.exp(-40.0 * t)
            val *= env
            
            # Layer 2: Tonal 'bloop' underneath (iOS-style resonance)
            bloop_freq = 600
            bloop = math.sin(2 * math.pi * bloop_freq * t) * math.exp(-25.0 * t) * 0.5
            
            audio.append((val + bloop) * 0.7)
        elif t < 0.25:
            # Tiny reverb tail — the bloop rings out softly
            bloop_freq = 600
            bloop = math.sin(2 * math.pi * bloop_freq * t) * math.exp(-15.0 * t) * 0.15
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
    print(f"Generating CTA text banner: {text}...")
    width, height = 850, 110
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Dark semi-transparent pill background with gold border
    draw_rounded_rect(draw, (0, 0, width, height), 25, (15, 15, 20, 220))
    draw.rounded_rectangle([2, 2, width-2, height-2], radius=25, outline=(255, 215, 0, 255), width=4)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 44)
    except:
        font = ImageFont.load_default()
        
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        
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

